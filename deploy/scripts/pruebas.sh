#!/usr/bin/env bash
# Corre las pruebas de la app.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env 2>/dev/null || true; set +a
SITE="${SITE_NAME:-antojate.localhost}"

docker compose exec -T backend bench --site "$SITE" set-config allow_tests true >/dev/null
docker compose exec -T backend bench --site "$SITE" run-tests --app antojate "$@"
