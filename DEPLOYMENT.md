# Deploying to the Oracle server

The whole app (API + front end) runs on one server with Docker Compose:

```
Internet ──▶ Caddy (:80/:443, auto-HTTPS)
              ├── /api/*  ──▶ FastAPI container (uvicorn :8000)
              ├── /docs, /openapi.json ──▶ FastAPI container
              └── everything else ──▶ static files from simple_budget_ui/dist
```

The database stays in Supabase — only hosting moves off AWS. Because Caddy
serves the UI and the API from the same origin, CORS is no longer needed in
production.

## One-time server setup

1. **Install Docker** (includes the compose plugin):

   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER   # log out/in afterwards
   ```

2. **Open ports 80 and 443.** On Oracle Cloud this means BOTH:
   - The VCN Security List / Network Security Group: add ingress rules for
     TCP 80 and 443 from 0.0.0.0/0 (Console → Networking → your VCN →
     Security Lists).
   - The instance's own firewall — Oracle's images ship with restrictive
     iptables rules that silently drop traffic even when the security list
     allows it:

     ```bash
     sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
     sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
     sudo netfilter-persistent save   # Ubuntu; on Oracle Linux use firewall-cmd
     ```

3. **Clone both repos side by side:**

   ```bash
   mkdir -p ~/apps && cd ~/apps
   git clone https://github.com/voidreamer/simple_budget.git
   git clone https://github.com/voidreamer/simple_budget_ui.git
   ```

4. **Configure the environment:**

   ```bash
   cd ~/apps/simple_budget
   cp .env.example .env
   nano .env   # set DATABASE_URL, SUPABASE_JWT_SECRET, DOMAIN
   ```

   Point your domain's DNS A record at the server's public IP. Caddy obtains
   and renews the TLS certificate automatically. No domain yet? Leave DOMAIN
   unset and the app serves plain HTTP on port 80.

5. **First deploy:**

   ```bash
   ./deploy.sh
   curl http://localhost/api/health   # → {"status":"ok"}
   ```

## Continuous deployment (GitHub Actions)

`.github/workflows/deploy.yml` SSHes into the server on every push to `main`
and runs `deploy.sh`, which pulls both repos, rebuilds the UI in a throwaway
Node container, and restarts Compose.

Add these repository secrets (Settings → Secrets and variables → Actions):

| Secret            | Value                                              |
|-------------------|----------------------------------------------------|
| `ORACLE_HOST`     | Server public IP or hostname                       |
| `ORACLE_USER`     | SSH user (e.g. `ubuntu` or `opc`)                  |
| `ORACLE_SSH_KEY`  | Private key with access to the server (PEM text)   |
| `ORACLE_SSH_PORT` | Optional, defaults to 22                           |
| `APP_URL`         | Optional, e.g. `https://budget.example.com` — enables the post-deploy health check |

The old AWS secrets (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`AWS_REGION`, `LAMBDA_FUNCTION_NAME`) can be deleted.

To redeploy when only the front end changed, trigger the workflow manually
(Actions → Deploy Backend → Run workflow) or set up the same SSH workflow in
`simple_budget_ui`.

## Changes required in simple_budget_ui

1. **API base URL**: point the API client at a relative path (`/api`) instead
   of the old API Gateway/Lambda URL. If it uses an env var (e.g.
   `VITE_API_URL`), set it to empty/`/` for production builds so requests go
   to the same origin, and keep `http://localhost:8000` for local dev.
2. **Remove AWS deploy config**: delete any S3-sync/CloudFront workflow —
   the UI is now built and served by this repo's `deploy.sh` + Caddy.
3. **Build output**: Compose mounts `../simple_budget_ui/dist` into Caddy.
   If the build outputs somewhere else, set `UI_DIST` in `.env` to that path.

## Day-2 operations

```bash
cd ~/apps/simple_budget
docker compose logs -f api      # API logs
docker compose logs -f caddy    # proxy/TLS logs
docker compose restart api      # restart just the API
./deploy.sh                     # manual redeploy
```

## Decommissioning AWS

Once the Oracle deployment is verified:

- Delete the Lambda function and its API Gateway.
- Delete the CloudFront distribution (`d1wqjnlllq13dm.cloudfront.net`) and
  the S3 bucket that fed it.
- Remove the AWS secrets from both GitHub repos.
