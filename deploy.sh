#!/usr/bin/env bash
# Deploys the budget app on the Oracle server.
# Expects this repo and simple_budget_ui cloned side by side, and a .env file
# next to this script (see .env.example). Requires only git + docker on the host.
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Updating backend"
git pull --ff-only origin main

UI_DIR="${UI_DIR:-../simple_budget_ui}"
if [ ! -d "$UI_DIR" ]; then
  echo "==> Cloning front-end"
  git clone https://github.com/voidreamer/simple_budget_ui.git "$UI_DIR"
fi

echo "==> Updating front-end"
git -C "$UI_DIR" pull --ff-only origin main

echo "==> Building front-end (containerized, no Node needed on host)"
docker run --rm \
  -v "$(cd "$UI_DIR" && pwd)":/app -w /app \
  node:20-alpine sh -c "npm ci && npm run build"

echo "==> Starting services"
docker compose up -d --build

docker compose ps
echo "==> Done"
