# Oracle Cloud Deployment (Budget API)

One-time setup to run the Simple Budget FastAPI backend on the existing Oracle
Cloud **Always-Free** VM (the same box that hosts the heybub/babylog API).
Pattern follows babylog's `docs/ORACLE_DEPLOYMENT.md`. No secrets in this file
— values come from `/opt/simple-budget/.env` on the VM.

## Target

- Backend: same Oracle `VM.Standard.E2.1.Micro` (1 OCPU / 1 GB, Always Free),
  Oracle Linux 9, as heybub-api. SSH: `opc@<ORACLE_HOST>` with the
  `heybub_oracle` key.
- Runtime: native Python 3.12 + uv venv + systemd (no Docker on the 1 GB box).
- App dir: `/opt/simple-budget`, service `simple-budget-api`,
  uvicorn on **127.0.0.1:8081** (heybub-api owns 8080).
- TLS/ingress: the existing **Cloudflare Tunnel** on the box gets one more
  ingress hostname (e.g. `budget-api.<your-domain>` → `http://localhost:8081`).
- DB/Auth: unchanged on Supabase (`DATABASE_URL`, `SUPABASE_JWT_SECRET`).
- Frontend: Cloudflare Pages (see `simple_budget-ui` repo) — not on this VM.

The host-prep steps from babylog (2 GB swap, kdump reclaim, uv install under
`/opt`) are already done on this box — do NOT repeat them.

## 1. App install (one time, single SSH session)

> The 1 GB box swap-thrashes under concurrent SSH sessions — do all of this in
> ONE serial session.

```sh
ssh -i ~/.ssh/heybub_oracle opc@<ORACLE_HOST>

sudo mkdir -p /opt/simple-budget && sudo chown opc:opc /opt/simple-budget
export PATH="$HOME/.local/bin:$PATH"
export UV_PYTHON_INSTALL_DIR=/opt/heybub/.uv-python   # reuse the shared /opt python store
uv python install 3.12
uv venv --python 3.12 /opt/simple-budget/.venv
```

Ship the code from your machine (or just let the GitHub Actions deploy job do
the first sync after the service file exists):

```sh
rsync -az --exclude '.git' --exclude '.github' --exclude '.idea' \
  --exclude '__pycache__' --exclude '.venv' \
  -e "ssh -i ~/.ssh/heybub_oracle" ./ opc@<ORACLE_HOST>:/opt/simple-budget/
```

Then on the VM:

```sh
cd /opt/simple-budget
cat > .env <<'EOF'
DATABASE_URL=postgresql://...          # the Supabase connection string (from the old Lambda console)
SUPABASE_JWT_SECRET=...                # the Supabase project's JWT secret (from the old Lambda console)
CORS_ORIGINS=https://<your-frontend-domain>,http://localhost:5173,http://localhost:3000
EOF
chmod 600 .env
uv pip install --python .venv/bin/python -r requirements.txt
sudo chcon -R -t bin_t /opt/simple-budget/.venv/bin   # SELinux: allow systemd to exec
```

## 2. systemd service

`/etc/systemd/system/simple-budget-api.service`:

```ini
[Unit]
Description=Simple Budget FastAPI backend
After=network-online.target
Wants=network-online.target

[Service]
User=opc
WorkingDirectory=/opt/simple-budget
ExecStart=/opt/simple-budget/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8081 --proxy-headers --forwarded-allow-ips '*'
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now simple-budget-api
curl -s localhost:8081/health    # -> {"status":"ok"}
```

## 3. Cloudflare Tunnel ingress

Add the budget API hostname to the existing tunnel config
(`/etc/cloudflared/config.yml`) **above** the fallback rule:

```yaml
ingress:
  - hostname: api.heybub.app
    service: http://localhost:8080
  - hostname: budget-api.<your-domain>        # NEW
    service: http://localhost:8081            # NEW
  - service: http_status:404
```

Route DNS for the new hostname and restart the tunnel:

```sh
cloudflared tunnel route dns --overwrite-dns heybub-oci budget-api.<your-domain>
sudo systemctl restart cloudflared
curl -s https://budget-api.<your-domain>/health
```

(If the budget app lives on a different Cloudflare zone than heybub.app, run
the `route dns` command from a machine logged into that zone, or add the CNAME
`budget-api -> <tunnel-UUID>.cfargotunnel.com` in the Cloudflare dashboard.)

## 4. GitHub Actions wiring (this repo)

- **Secrets:** `ORACLE_SSH_KEY` = contents of `~/.ssh/heybub_oracle` (the
  private key). The old `AWS_*`/`LAMBDA_FUNCTION_NAME` secrets are only needed
  if you re-enable the Lambda path.
- **Variables:** `ORACLE_HOST` = the VM public IP;
  `API_URL` = `https://budget-api.<your-domain>` (enables the post-deploy
  public health check); leave `DEPLOY_AWS` unset (the AWS job stays off).

After that, every push to `main` rsyncs the code to the VM, installs deps into
the venv, restarts `simple-budget-api`, and health-checks it.

## 5. Frontend cutover

In `simple_budget-ui`, set the `VITE_API_BASE_URL` secret to
`https://budget-api.<your-domain>/api` (note the `/api` suffix — the frontend
appends paths directly to it) and deploy; see that repo's workflow. Then make
sure this backend's `CORS_ORIGINS` in `/opt/simple-budget/.env` contains the
frontend's origin, and `sudo systemctl restart simple-budget-api`.

## 6. AWS teardown (after the cutover is verified)

- Delete the Lambda function + API Gateway/function URL for the budget API.
- Empty + delete the frontend S3 bucket, disable + delete the CloudFront
  distribution (`d1wqjnlllq13dm.cloudfront.net`).
- Remove the now-unused `AWS_*`, `LAMBDA_FUNCTION_NAME`, `S3_BUCKET_NAME`,
  `CLOUDFRONT_DISTRIBUTION_ID` GitHub secrets from both repos.

## Operator cheatsheet

```sh
ssh -i ~/.ssh/heybub_oracle opc@<ORACLE_HOST>

sudo systemctl restart simple-budget-api
systemctl status simple-budget-api --no-pager
sudo journalctl -u simple-budget-api -n 50 --no-pager
curl -s localhost:8081/health                      # on-box
curl -s https://budget-api.<your-domain>/health    # public (tunnel)
```

If SSH won't connect (box swap-thrashing), reboot from the OCI console — both
this service and heybub's come back automatically (`systemctl enable`d).
