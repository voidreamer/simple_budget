FAST-API backend portion for simple budget. the front end made in react is: https://github.com/voidreamer/simple_budget-ui
This api uses sqlalchemy to connect to a custom database in supabase

## Deployment

Runs as a systemd service (`simple-budget-api`) on an Oracle Cloud Always-Free
VM, exposed through a Cloudflare Tunnel. Pushes to `main` deploy automatically
via GitHub Actions (rsync + service restart). See
[docs/ORACLE_DEPLOYMENT.md](docs/ORACLE_DEPLOYMENT.md) for the one-time server
setup, required GitHub secrets/variables, and the operator cheatsheet.

The previous AWS Lambda deploy path is kept in the workflow but disabled
(repo variable `DEPLOY_AWS` unset); `handler.py` (Mangum) remains as a
fallback entry point.

Run locally:

```sh
pip install -r requirements.txt
# .env needs DATABASE_URL and SUPABASE_JWT_SECRET
uvicorn app.main:app --reload --port 8001
```
