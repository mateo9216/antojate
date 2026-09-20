#!/usr/bin/env bash
# Publica la tienda local en una URL https temporal de Cloudflare.
# Gratis, sin cuenta, sin dominio y sin tarjeta. La URL vive mientras el
# contenedor esté arriba y cambia cada vez que se reinicia.
set -euo pipefail

cd "$(dirname "$0")/.."
set -a; . ./.env 2>/dev/null || true; set +a

echo "==> Levantando el túnel"
# Se recrea el contenedor a propósito: si se reutiliza, sus logs conservan las
# URLs de arranques anteriores y terminás probando una dirección ya muerta.
docker compose stop cloudflared >/dev/null 2>&1 || true
docker compose rm -f cloudflared >/dev/null 2>&1 || true
docker compose --profile tunnel up -d cloudflared >/dev/null

echo "==> Esperando la URL pública"
URL=""
for i in $(seq 1 30); do
  URL=$(docker compose logs cloudflared 2>&1 \
        | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1 || true)
  [ -n "$URL" ] && break
  sleep 2
done

if [ -z "$URL" ]; then
  echo "No se pudo leer la URL. Mirá: docker compose logs cloudflared"
  exit 1
fi

echo "==> Comprobando que responda"
ESTADO="sin respuesta"
for i in $(seq 1 10); do
  CODIGO=$(curl -sL -o /dev/null -w '%{http_code}' --max-time 15 "$URL/tienda" || echo 000)
  if [ "$CODIGO" = "200" ]; then ESTADO="OK"; break; fi
  sleep 3
done

cat <<FIN

  URL para el cliente:  $URL/tienda
  Estado:               $ESTADO

  Mientras el túnel esté arriba, esa dirección muestra la tienda de tu máquina.
  Para bajarlo:  docker compose stop cloudflared

  ─────────────────────────────────────────────────────────────────────────
  ANTES DE MANDAR ESA URL

  Esto queda abierto a internet: cualquiera con el enlace entra, incluido
  /app. Si la contraseña de Administrator sigue siendo la de desarrollo,
  cambiala primero:

      ./scripts/bench set-admin-password '<una contraseña buena>'
  ─────────────────────────────────────────────────────────────────────────

  Wompi necesita una URL pública para mandar el webhook de confirmación.
  Cargá esta en el panel de Wompi (sandbox) como URL de eventos:
      $URL/api/method/antojate.api.pagos.webhook_wompi

FIN
