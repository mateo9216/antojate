#!/usr/bin/env bash
# Aplica doctypes nuevos o modificados y recarga el código.
# Correlo cada vez que agregues o cambies un doctype o un custom field.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env 2>/dev/null || true; set +a

echo "==> Migrando el sitio"
docker compose exec -T backend bench --site "${SITE_NAME:-antojate.localhost}" migrate

echo "==> Reaplicando campos personalizados"
docker compose exec -T backend bench --site "${SITE_NAME:-antojate.localhost}" \
  console <<'PY' >/dev/null 2>&1 || true
from antojate.install import after_install; after_install()
PY

./scripts/recargar.sh
