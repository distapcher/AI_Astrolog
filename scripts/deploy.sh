#!/usr/bin/env bash
# Deploy AI Astrolog bot: commit + push + update on VPS.
#
# Usage:
#   ./scripts/deploy.sh
#   ./scripts/deploy.sh "fix chart formatting"
#
# Optional:
#   DEPLOY_HOST=root@2.27.25.85
#   DEPLOY_DIR=/opt/AI_Astrolog
#   DEPLOY_BRANCH=main

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DEPLOY_HOST="${DEPLOY_HOST:-root@2.27.25.85}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/AI_Astrolog}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
COMMIT_MSG="${1:-Update AI Astrolog bot}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: not a git repository: $ROOT" >&2
  exit 1
fi

echo "== Git: stage & commit =="
git add -A
if git diff --staged --quiet; then
  echo "No file changes to commit."
else
  git commit -m "$COMMIT_MSG"
fi

echo "== Git: push to origin/$DEPLOY_BRANCH =="
git push -u origin "$DEPLOY_BRANCH"

echo "== Server: pull & restart ($DEPLOY_HOST) =="
ssh "$DEPLOY_HOST" bash -s <<EOF
set -euo pipefail
cd "$DEPLOY_DIR"
git fetch origin
git checkout "$DEPLOY_BRANCH"
git pull --ff-only origin "$DEPLOY_BRANCH"
docker compose up -d --build
docker compose ps
docker compose logs --tail=30
EOF

echo "== Done =="
