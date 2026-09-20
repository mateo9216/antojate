#!/usr/bin/env bash
# Carga el catálogo de ejemplo: compañía, productos con variantes, existencias
# y ciudades de envío. Es idempotente.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env 2>/dev/null || true; set +a

docker compose exec -T backend bench --site "${SITE_NAME:-antojate.localhost}" console <<'PY'
from antojate.demo import cargar; cargar()
PY
# La carga marca la configuración como terminada, pero los procesos que ya
# están corriendo siguen sirviendo el arranque viejo: sin esto, el escritorio
# manda al asistente de configuración aunque en la base ya esté completo.
echo "==> Limpiando caché y recargando"
docker compose exec -T backend bench --site "${SITE_NAME:-antojate.localhost}" clear-cache >/dev/null
./scripts/recargar.sh

