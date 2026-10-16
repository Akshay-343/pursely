#!/usr/bin/env bash
# Runs ON THE SERVER (streamed over SSH by .github/workflows/deploy.yml).
# Expects: REGISTRY_USER, REGISTRY_TOKEN, IMAGE_API, IMAGE_WEB; optional DEPLOY_PATH.
set -euo pipefail

cd "${DEPLOY_PATH:-$HOME/Moneytracker}"

echo "$REGISTRY_TOKEN" | docker login ghcr.io -u "$REGISTRY_USER" --password-stdin
trap 'docker logout ghcr.io >/dev/null 2>&1 || true' EXIT

git fetch --quiet origin main && git merge --ff-only origin/main   # picks up compose/Caddy changes

export IMAGE_API IMAGE_WEB
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.deploy.yml"
$COMPOSE pull api web
$COMPOSE up -d --remove-orphans
$COMPOSE ps
docker image prune -f >/dev/null
