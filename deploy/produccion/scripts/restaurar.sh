#!/usr/bin/env bash
# Restaura el sitio desde un respaldo.
#
#   ./scripts/restaurar.sh respaldos/20260920-030000
#
# DESTRUCTIVO: reemplaza la base de datos actual por la del respaldo.
set -euo pipefail
cd "$(dirname "$0")/.."

CARPETA="${1:-}"
[ -n "$CARPETA" ] && [ -d "$CARPETA" ] || {
  echo "Uso: $0 <carpeta-del-respaldo>"
  echo "Disponibles:"; ls -1dt respaldos/*/ 2>/dev/null | head -10
  exit 1
}

set -a; . ./.env; set +a
: "${DOMINIO:?falta DOMINIO}"
: "${DB_ROOT_PASSWORD:?falta DB_ROOT_PASSWORD}"

SQL=$(ls "$CARPETA"/*database.sql.gz 2>/dev/null | head -1 || true)
[ -n "$SQL" ] || { echo "No hay archivo de base de datos en $CARPETA"; exit 1; }
ARCHIVOS=$(ls "$CARPETA"/*files.tar 2>/dev/null | head -1 || true)

echo
echo "  Se va a REEMPLAZAR la base de datos de $DOMINIO"
echo "  con el respaldo: $(basename "$SQL")"
echo
read -r -p "  Escribí RESTAURAR para continuar: " confirmacion
[ "$confirmacion" = "RESTAURAR" ] || { echo "Cancelado."; exit 1; }

dc() { docker compose -f compose.yaml "$@"; }
CONTENEDOR=$(dc ps -q backend)

echo "==> Copiando el respaldo al contenedor"
docker exec "$CONTENEDOR" mkdir -p /tmp/restauracion
docker cp "$SQL" "$CONTENEDOR:/tmp/restauracion/"
[ -n "$ARCHIVOS" ] && docker cp "$ARCHIVOS" "$CONTENEDOR:/tmp/restauracion/"

echo "==> Restaurando"
ORDEN="bench --site $DOMINIO restore /tmp/restauracion/$(basename "$SQL") \
  --db-root-username root --db-root-password '$DB_ROOT_PASSWORD' --force"
[ -n "$ARCHIVOS" ] && ORDEN="$ORDEN --with-private-files /tmp/restauracion/$(basename "$ARCHIVOS")"
dc exec -T backend bash -c "$ORDEN"

echo "==> Migrando y limpiando caché"
dc exec -T backend bench --site "$DOMINIO" migrate
dc exec -T backend bench --site "$DOMINIO" clear-cache
dc exec -T backend rm -rf /tmp/restauracion

echo "Listo. Verificá https://$DOMINIO/tienda"
