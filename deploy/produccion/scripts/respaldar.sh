#!/usr/bin/env bash
# Respalda base de datos y archivos subidos (las fotos de los productos).
#
# Guarda las copias fuera del volumen de Docker, en ./respaldos, y conserva
# las últimas RETENCION. Pensado para correr por cron todas las noches.
set -euo pipefail
cd "$(dirname "$0")/.."

set -a; . ./.env 2>/dev/null || true; set +a
: "${DOMINIO:?falta DOMINIO}"
RETENCION="${RETENCION:-14}"

DESTINO="respaldos"
mkdir -p "$DESTINO"
dc() { docker compose -f compose.yaml "$@"; }

echo "==> Generando el respaldo"
dc exec -T backend bench --site "$DOMINIO" backup --with-files >/dev/null

# bench los deja dentro del volumen; hay que sacarlos de ahí. Un respaldo que
# vive en el mismo disco que la base no es un respaldo.
echo "==> Copiando fuera del contenedor"
CONTENEDOR=$(dc ps -q backend)
MARCA=$(date +%Y%m%d-%H%M%S)
CARPETA="$DESTINO/$MARCA"
mkdir -p "$CARPETA"

docker exec "$CONTENEDOR" bash -c \
  "ls -t /home/frappe/frappe-bench/sites/$DOMINIO/private/backups/* | head -4" \
  | while read -r archivo; do
      docker cp "$CONTENEDOR:$archivo" "$CARPETA/" 2>/dev/null || true
    done

echo "==> Rotando (se conservan $RETENCION)"
ls -1dt "$DESTINO"/*/ 2>/dev/null | tail -n +$((RETENCION + 1)) | xargs -r rm -rf

TAMANO=$(du -sh "$CARPETA" | cut -f1)
echo "Listo: $CARPETA ($TAMANO)"

cat <<'AVISO'

  Un respaldo que solo vive en este servidor no protege de que el servidor
  se pierda. Copiá ./respaldos a otro lado (S3, Backblaze, otra máquina)
  y probá una restauración de verdad al menos una vez.

AVISO
