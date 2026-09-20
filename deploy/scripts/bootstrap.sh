#!/usr/bin/env bash
# Levanta Antójate de cero en la máquina local. Es idempotente: si el sitio ya
# existe no lo vuelve a crear, así que se puede correr las veces que haga falta.
set -euo pipefail

cd "$(dirname "$0")/.."

# --demo deja el sitio con catálogo de ejemplo, listo para mostrar.
CARGAR_DEMO="no"
# Con `set -e`, un `[ ... ] && x` que da falso abortaría el script entero.
if [ "${1:-}" = "--demo" ]; then CARGAR_DEMO="si"; fi

[ -f .env ] || { echo "==> Creando .env a partir de .env.example"; cp .env.example .env; }
set -a; . ./.env; set +a

SITE_NAME="${SITE_NAME:-antojate.localhost}"
HTTP_PORT="${HTTP_PORT:-8080}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-admin}"

dc() { docker compose "$@"; }

echo "==> 1/5 Construyendo la imagen (ERPNext + app antojate)"
dc build

echo "==> 2/5 Levantando servicios"
dc up -d

echo "==> 3/5 Esperando a que el backend responda"
for i in $(seq 1 60); do
  if dc exec -T backend bench --version >/dev/null 2>&1; then break; fi
  [ "$i" = 60 ] && { echo "ERROR: el backend no arrancó. Revisá: docker compose logs backend"; exit 1; }
  sleep 5
done

echo "==> 4/5 Preparando el sitio $SITE_NAME"
if dc exec -T backend test -d "sites/$SITE_NAME"; then
  echo "    El sitio ya existe, no se recrea."
else
  dc exec -T backend bench new-site "$SITE_NAME" \
    --mariadb-user-host-login-scope='%' \
    --db-root-username=root \
    --db-root-password="$DB_ROOT_PASSWORD" \
    --admin-password="$ADMIN_PASSWORD" \
    --install-app erpnext \
    --install-app antojate \
    --set-default
fi

echo "==> 5/5 Ajustes de desarrollo"
# developer_mode permite que los cambios en doctypes se escriban a disco,
# que es lo que hace que queden versionados en git y no solo en la base.
dc exec -T backend bench --site "$SITE_NAME" set-config developer_mode 1
dc exec -T backend bench --site "$SITE_NAME" clear-cache

if [ "$CARGAR_DEMO" = "si" ]; then
  echo "==> Cargando datos de demostración"
  ./scripts/datos-demo.sh
fi

cat <<FIN

  Listo.

  Tienda        http://$SITE_NAME:$HTTP_PORT/tienda
  Escritorio    http://$SITE_NAME:$HTTP_PORT/desk
  Usuario       Administrator
  Contraseña    $ADMIN_PASSWORD

  Si el catálogo está vacío, cargá los datos de ejemplo:
      ./scripts/datos-demo.sh

  Para mostrarle la tienda al cliente desde internet:
      ./scripts/tunnel.sh

FIN
