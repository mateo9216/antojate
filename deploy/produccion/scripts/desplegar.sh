#!/usr/bin/env bash
# Publica una versión nueva del código en el servidor.
#
#   git pull && ./scripts/desplegar.sh
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "Falta .env."; exit 1; }
set -a; . ./.env; set +a
: "${DOMINIO:?falta DOMINIO}"

dc() { docker compose -f compose.yaml "$@"; }

echo "==> Respaldando antes de tocar nada"
./scripts/respaldar.sh

echo "==> Construyendo la imagen nueva"
dc build

echo "==> Activando el modo mantenimiento"
# Durante la migración la base cambia de forma. Sin esto, un comprador que
# esté pagando en ese momento puede toparse con un error a mitad del checkout.
dc exec -T backend bench --site "$DOMINIO" set-maintenance-mode on || true

echo "==> Reemplazando los contenedores"
dc up -d --force-recreate

echo "==> Esperando al backend"
for i in $(seq 1 60); do
  dc exec -T backend bench --version >/dev/null 2>&1 && break
  sleep 5
done

echo "==> Migrando"
dc exec -T backend bench --site "$DOMINIO" migrate

echo "==> Reaplicando campos personalizados"
dc exec -T backend bench --site "$DOMINIO" console <<'PYFIN' >/dev/null 2>&1 || true
from antojate.install import after_install; after_install()
PYFIN

echo "==> Saliendo del modo mantenimiento"
dc exec -T backend bench --site "$DOMINIO" set-maintenance-mode off
dc exec -T backend bench --site "$DOMINIO" clear-cache

echo "==> Comprobando que la tienda responda"
ESTADO=$(curl -sL -o /dev/null -w '%{http_code}' --max-time 20 "https://$DOMINIO/tienda" || echo 000)
echo "    https://$DOMINIO/tienda -> $ESTADO"
[ "$ESTADO" = "200" ] || { echo "OJO: la tienda no responde 200. Revisá los registros."; exit 1; }

echo "Listo."
