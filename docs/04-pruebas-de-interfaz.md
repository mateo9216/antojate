# Pruebas de interfaz y recorridos grabados

Además de las pruebas de Python, hay pruebas que manejan un navegador real
contra la tienda corriendo. Sirven para dos cosas a la vez:

1. **Probar de verdad** lo que ningún `curl` alcanza a ver: que el JavaScript
   cargue, que el carrito sume, que el checkout arme el cobro.
2. **Dejar un video narrado** de cada recorrido, para mostrarle la tienda al
   cliente sin tener que estar al lado explicando.

Lo segundo es un subproducto de lo primero, y eso es lo que las hace confiables:
**si la tienda se rompe, la prueba falla y el video no se genera**. No hay forma
de que el video muestre algo que ya no funciona.

## Correrlas

La tienda tiene que estar arriba (`deploy/scripts/bootstrap.sh`).

```bash
cd pruebas-ui
npm install        # solo la primera vez
./correr.sh
```

Todo pasa dentro del contenedor oficial de Playwright, que ya trae el navegador.
No hay que instalar Chrome ni nada más: solo Docker.

Al terminar, abrí **`pruebas-ui/videos/index.html`**.

```bash
./correr.sh tests/01-recorrido-de-compra.spec.js   # una sola
./correr.sh --project=celular                      # solo las de teléfono
SLOW_MO=0 PAUSA=0 ./correr.sh                      # rápido, sin narración
npx playwright show-report pruebas-ui/informe      # el informe detallado
```

`SLOW_MO=0 PAUSA=0` es lo que conviene en integración continua: los videos
narrados existen para que los vea una persona, no un servidor.

## Los cuatro recorridos

| Archivo | Qué prueba y qué muestra |
|---|---|
| `01-recorrido-de-compra` | Catálogo, filtro por categoría, producto con presentaciones, carrito, checkout con envío y el cobro firmado que se le entrega a Wompi |
| `02-como-esta-disenado` | El escritorio de ERPNext: dónde vive el producto, las llaves de pago, las ciudades y los pedidos |
| `03-defensas` | Intentos reales de hacer trampa y qué responde la tienda |
| `04-en-el-celular` | La misma tienda en un teléfono, sin desbordes horizontales |

## Qué se afirma de verdad

Los carteles del video son narración; lo que sostiene la prueba son las
aserciones. Entre otras:

- El catálogo publica exactamente los productos marcados, y el filtro por
  categoría los reduce a los correctos.
- Un producto con presentaciones **no se puede agregar** hasta escoger una, y
  al escogerla cambian precio y disponibilidad.
- El contador del carrito refleja las unidades agregadas.
- Al confirmar el checkout, la tienda redirige a Wompi con `currency=COP`,
  una llave pública `pub_test_`, un monto mayor que cero, una referencia que
  empieza por `SAL-ORD-` y una **firma de 64 caracteres hexadecimales**.
- El carrito guardado en el navegador contiene **solo** `item_code` y `qty`:
  se verifica campo por campo que no haya un precio manipulable.
- Pedir 999 unidades de algo que tiene menos hace que el servidor **recorte la
  cantidad** y lo avise.
- El pedido de un comprador responde **404 sin el token correcto**, aunque el
  número de pedido sea real y consecutivo.
- En teléfono, ninguna página desborda a lo ancho.

## Tres problemas reales que aparecieron gracias a esto

Ninguno se veía con `curl`, porque el HTML se servía perfecto en los tres casos.

### 1. El carrito y el checkout no funcionaban en un navegador

La primera corrida falló con `Antojate is not defined`.

Frappe inyecta el JavaScript declarado en `web_include_js` **al final del
`<body>`**, después de los scripts propios de cada página. Como esas páginas
llaman a `Antojate.*` apenas se leen, la función todavía no existía. En la
práctica: **el carrito no cargaba y no se podía comprar**.

Se corrigió cargando el script en el `<head>` desde `templates/tienda_base.html`.

### 2. El cliente habría caído en el asistente de configuración

Al abrir el escritorio, en vez del panel aparecía el asistente de configuración
inicial de ERPNext, en bucle.

En Frappe v16 `is_setup_complete()` ya no mira `System Settings`: recorre el
doctype **`Installed Application`** y exige que `frappe` y `erpnext` tengan su
propia bandera `is_setup_complete` en 1. Correr el asistente por código no
siempre las deja marcadas.

Se corrigió en `demo.py` (`marcar_configuracion_terminada`). Además hay que
limpiar el caché después: los procesos ya arrancados siguen sirviendo el
arranque viejo, y el asistente reaparece aunque en la base ya esté resuelto.
Eso lo hace ahora `deploy/scripts/datos-demo.sh` solo.

### 3. El escritorio ya no está en `/app`

En Frappe v16 vive en **`/desk`**; `/app` responde con una redirección 301.
La documentación decía `/app` y quedó corregida en todos lados.

## Dos trampas del entorno, que no son bugs

- **El escritorio es una SPA.** `page.goto` vuelve mucho antes de que el
  formulario exista, y saliendo de una ruta del escritorio una navegación normal
  se cancela sola (`ERR_ABORTED`). Por eso las pruebas usan
  `waitUntil: "commit"` y esperan por contenido, no por el evento `load`.
- **`socket.io` rechaza el origen** cuando se entra como `http://frontend:8080`
  desde dentro de Docker, porque Frappe compara el host con el nombre del sitio.
  Ensucia la consola con errores, pero no impide que el escritorio funcione. Un
  usuario real, que entra por el nombre del sitio, no lo ve.
