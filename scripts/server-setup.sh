#!/usr/bin/env bash
# First-time setup on VPS (run on server as root).
#
#   curl -fsSL https://raw.githubusercontent.com/distapcher/AI_Astrolog/main/scripts/server-setup.sh | bash
#
# Or after cloning:
#   REPO_URL=https://github.com/distapcher/AI_Astrolog.git DEPLOY_DIR=/opt/AI_Astrolog bash scripts/server-setup.sh

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/distapcher/AI_Astrolog.git}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/AI_Astrolog}"
BRANCH="${BRANCH:-main}"

if [[ -d "$DEPLOY_DIR/.git" ]]; then
  cd "$DEPLOY_DIR"
  git pull --ff-only origin "$BRANCH" || true
else
  git clone --branch "$BRANCH" "$REPO_URL" "$DEPLOY_DIR"
  cd "$DEPLOY_DIR"
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from example — edit $DEPLOY_DIR/.env before starting."
fi

docker compose up -d --build
docker compose ps
