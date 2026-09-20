#!/usr/bin/env bash
# Crea el sitio en el servidor. Se corre UNA sola vez, la primera.
#
# Para actualizaciones posteriores está desplegar.sh.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "Falta .env. Copiá .env.example y completalo."; exit 1; }
set -a; . ./.env; set +a

: "${DOMINIO:?falta DOMINIO}"
: "${ADMIN_PASSWORD:?falta ADMIN_PASSWORD}"
: "${DB_ROOT_PASSWORD:?falta DB_ROOT_PASSWORD}"

dc() { docker compose -f compose.yaml "$@"; }

if dc exec -T backend test -d "sites/$DOMINIO" 2>/dev/null; then
  echo "El sitio $DOMINIO ya existe. Para actualizar, usá desplegar.sh."
  exit 0
fi

echo "==> 1/5 Construyendo la imagen"
dc build

echo "==> 2/5 Levantando servicios"
dc up -d

echo "==> 3/5 Esperando al backend"
for i in $(seq 1 60); do
  dc exec -T backend bench --version >/dev/null 2>&1 && break
  [ "$i" = 60 ] && { echo "El backend no arrancó. Revisá: docker compose logs backend"; exit 1; }
  sleep 5
done

echo "==> 4/5 Creando el sitio $DOMINIO"
dc exec -T backend bench new-site "$DOMINIO" \
  --mariadb-user-host-login-scope='%' \
  --db-root-username=root \
  --db-root-password="$DB_ROOT_PASSWORD" \
  --admin-password="$ADMIN_PASSWORD" \
  --install-app erpnext \
  --install-app antojate \
  --set-default

echo "==> 5/5 Ajustes de producción"
# host_name es importante y se olvida: los trabajos en segundo plano no tienen
# una petición HTTP de la cual deducir el dominio. Sin esto, la URL de regreso
# que se le manda a Wompi y los enlaces de los correos salen mal.
dc exec -T backend bench --site "$DOMINIO" set-config host_name "https://$DOMINIO"
dc exec -T backend bench --site "$DOMINIO" set-config developer_mode 0
dc exec -T backend bench --site "$DOMINIO" clear-cache

cat <<FIN

  Sitio creado.

  Tienda      https://$DOMINIO/tienda
  Escritorio  https://$DOMINIO/desk   (Administrator)

  Falta lo que no se puede automatizar. En orden:

   1. Configurar la compañía en el asistente de ERPNext (moneda COP,
      país Colombia, zona horaria America/Bogota).
   2. Cargar las llaves de PRODUCCIÓN de Wompi y cambiar el ambiente.
   3. Registrar el webhook en el panel de Wompi:
        https://$DOMINIO/api/method/antojate.api.pagos.webhook_wompi
   4. Configurar el correo saliente, o el comprador nunca recibe nada.
   5. Programar los respaldos (scripts/respaldar.sh).

  El detalle completo está en docs/06-produccion.md.

FIN
