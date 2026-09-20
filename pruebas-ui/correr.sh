#!/usr/bin/env bash
# Corre las pruebas de interfaz y graba los videos.
#
# Todo pasa dentro del contenedor oficial de Playwright, que ya trae el
# navegador: no hay que instalar nada en la máquina.
set -euo pipefail
cd "$(dirname "$0")"

VERSION=$(node -e "console.log(require('@playwright/test/package.json').version)")
IMAGEN="mcr.microsoft.com/playwright:v${VERSION}-noble"

if ! docker image inspect "$IMAGEN" >/dev/null 2>&1; then
  echo "==> Descargando $IMAGEN (una sola vez)"
  docker pull "$IMAGEN"
fi

# Se conecta a la red de la tienda y le habla al frontend por su nombre.
# nginx sirve el mismo sitio sin importar el Host, así que funciona igual.
echo "==> Corriendo las pruebas"
# Se guarda el código de salida en vez de dejar que `set -e` corte acá: aunque
# una prueba falle, los videos que sí se grabaron valen, y el de la que falló
# muestra exactamente dónde se rompió.
CODIGO=0
docker run --rm \
  --network antojate \
  -e BASE_URL="${BASE_URL:-http://frontend:8080}" \
  -e SLOW_MO="${SLOW_MO:-260}" \
  -e PAUSA="${PAUSA:-1800}" \
  -v "$PWD":/trabajo \
  -w /trabajo \
  "$IMAGEN" \
  npx playwright test "$@" || CODIGO=$?

echo
echo "==> Organizando los videos"
node ayudas/galeria.mjs

if [ "$CODIGO" != "0" ]; then
  echo
  echo "Hubo pruebas en rojo. El detalle, con capturas y traza:"
  echo "    npx playwright show-report informe"
fi
exit "$CODIGO"
