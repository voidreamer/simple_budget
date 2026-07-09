# Simple Budget — API

FastAPI backend for simple budget. The React front end lives at
https://github.com/voidreamer/simple_budget_ui.

Uses SQLAlchemy to connect to a Postgres database in Supabase, and Supabase
JWTs for auth.

## Hosting

Runs on a self-hosted Oracle server with Docker Compose: the API container
(uvicorn) sits behind Caddy, which also serves the built front end and
handles HTTPS. See [DEPLOYMENT.md](DEPLOYMENT.md) for server setup and the
GitHub Actions deploy pipeline.

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL and SUPABASE_JWT_SECRET
uvicorn app.main:app --reload
```

API docs at http://localhost:8000/docs.
