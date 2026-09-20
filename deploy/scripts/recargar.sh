#!/usr/bin/env bash
# Aplica los cambios de código al sitio.
#
# Los procesos de Python cargan la app en memoria al arrancar, así que editar
# un .py no se refleja solo: hay que reiniciarlos. Las plantillas .html y los
# .css/.js sí se leen en cada petición y no necesitan esto.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Reiniciando procesos de Python"
# El frontend entra también: nginx resuelve la IP del backend al arrancar, y
# al reiniciar el backend cambia de IP. Si no se reinicia, responde 502.
docker compose restart backend websocket scheduler queue-short queue-long >/dev/null
docker compose restart frontend >/dev/null

echo "==> Esperando a que el sitio responda"
set -a; . ./.env 2>/dev/null || true; set +a
PUERTO="${HTTP_PORT:-8080}"
SITIO="${SITE_NAME:-antojate.localhost}"
for i in $(seq 1 30); do
  CODIGO=$(curl -s -o /dev/null -w '%{http_code}' \
           -H "Host: $SITIO" "http://localhost:$PUERTO/tienda" || echo 000)
  [ "$CODIGO" = "200" ] && break
  sleep 2
done
echo "    /tienda responde $CODIGO"

echo "Listo."
