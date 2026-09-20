# Antójate — análisis y arquitectura

Documento de decisiones. Fecha: 2026-09-19.

## 1. Qué vamos a construir

Una tienda en línea para el cliente **Antójate**: catálogo mixto (varias categorías),
productos con variantes, inventario real y envío a domicilio, con pago en línea por
**Nequi y Bancolombia**.

Decisiones ya cerradas con el equipo:

| Tema | Decisión |
|---|---|
| Base | Sitio **Frappe/ERPNext v16 nuevo**, con app custom `antojate` |
| Pagos | Pasarela automática, arrancando en **sandbox** (sin costo ni afiliación) |
| Catálogo | Mixto / general, con variantes y control de stock |
| Entrega | Producto físico con envío |
| Dueño | Cliente externo; el desarrollo vive en esta carpeta |
| Hosting | **Sin presupuesto por ahora**: local + URL pública temporal |

## 2. La restricción que manda: costo cero

No hay con qué pagar hosting todavía, y eso define el despliegue en tres fases.
Lo importante es que **la arquitectura no cambia entre fases**: es el mismo sitio
Frappe, el mismo código y la misma base de datos. Solo cambia dónde corre.

```
FASE 1 — HOY: desarrollo local, costo 0
  Tu Mac
    └── Docker: ERPNext v16 + app antojate + MariaDB + Redis
         http://antojate.localhost:8080

FASE 2 — DEMO AL CLIENTE: costo 0
  Tu Mac + túnel de Cloudflare
    └── https://<aleatorio>.trycloudflare.com  ──► el cliente lo abre desde su casa
        (vive mientras tu máquina esté encendida; sin cuenta, dominio ni tarjeta)

FASE 3 — PRODUCCIÓN: cuando el cliente pueda pagar
  VPS (~20-40 USD/mes) o el GKE que ya operan
    └── mismo docker compose + dominio propio + TLS + backups
```

El salto de la fase 2 a la 3 es una restauración de backup y un cambio de DNS.
Nada del código se reescribe.

## 3. Arquitectura

```
                         NAVEGADOR DEL COMPRADOR
                                   │
                                   ▼
                        nginx (contenedor frontend)
                                   │
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
     STOREFRONT PÚBLICO                        ESCRITORIO ERPNEXT
     /tienda  /producto/<x>                    /app
     /carrito /checkout                        (lo usa el cliente para
     /mi-pedido/<x>                             cargar productos y
              │                                 despachar pedidos)
              ▼
     ┌─────────────────────────────────────────────────┐
     │  app antojate  (lo que escribimos nosotros)     │
     │   · páginas del storefront                      │
     │   · carrito y checkout                          │
     │   · integración de pagos + webhook              │
     │   · reglas de envío por ciudad                  │
     └─────────────────────────────────────────────────┘
              │ usa, sin modificar
              ▼
     ┌─────────────────────────────────────────────────┐
     │  ERPNext v16  (lo que NO tocamos)               │
     │   Item · Item Variant · Bin (stock)             │
     │   Customer · Sales Order · Sales Invoice        │
     │   Payment Entry · Shipping Rule                 │
     └─────────────────────────────────────────────────┘
              │
              ▼
        MariaDB + Redis
```

La regla de oro: **la app `antojate` extiende, nunca reemplaza**. Todo lo que
ERPNext ya sabe hacer (stock, precios, impuestos, pedidos, contabilidad) se usa
tal cual. Nosotros ponemos la cara pública y el cobro.

## 4. Por qué esta base

**Lo que ganamos gratis con ERPNext**, y que en una tienda a medida habría que
construir: inventario con reserva y descuento automático, variantes por atributos,
listas de precios, impuestos (IVA), clientes, pedidos, facturación, reglas de
envío, y un panel de administración completo donde el cliente carga productos sin
que nosotros intervengamos.

**Lo que ponemos nosotros**: el storefront. Aquí hay una decisión de peso.

### El storefront: app propia, no `webshop`

ERPNext tuvo un módulo de e-commerce que hoy vive aparte, en la app `webshop`.
Verificamos su estado real antes de decidir (no de oído):

- **Sí existe rama `version-16`**, y la imagen que usamos trae Python 3.14.2, así
  que instalaría sin problema. La incompatibilidad no es el argumento.
- Pero esa rama **se creó hace cuatro días** (mediados de septiembre de 2026), el
  repositorio **no publica ningún tag ni release**, y el **CI nunca se ha
  ejecutado sobre su HEAD**: las únicas corridas son las de los PR de backport, y
  la mayoría están en rojo.
- `webshop` arrastra además la app `payments` como dependencia obligatoria.

Montar la tienda de un cliente sobre una rama sin versionar, sin CI verde y con
cuatro días de vida es apostar. Y aunque saliera bien, quedan dos razones de peso:

1. **Diseño.** Su portal es una plantilla Bootstrap genérica. Para que quede como
   una tienda de verdad habría que sobrescribir casi todas sus plantillas, con lo
   cual el ahorro se evapora.
2. **Superficie.** Trae wishlist, comparador y portal de cliente que este proyecto
   no pidió, y que igual hay que mantener y asegurar.

Escribir el storefront son unas seis páginas sobre las plantillas de portal que
Frappe ya trae. Es trabajo acotado y nos deja el control del diseño, que es
justo lo que un cliente juzga.

### El cobro: integración propia, sin la app `payments`

ERPNext tiene un camino canónico para pasarelas: la app `payments` + `Payment
Request` + `Payment Gateway Account`. Lo evaluamos y lo descartamos para este
proyecto: suma otra app con el mismo problema de madurez en v16, y su ciclo
(Quotation → Payment Request → Payment Entry) es más maquinaria de la que esta
tienda necesita.

Hablamos con Wompi directamente desde nuestra app y creamos el `Payment Entry`
nosotros. Es menos código, sin dependencias nuevas, y no impide volver al camino
canónico después si el cliente crece.

## 5. Modelo de datos

**De ERPNext, sin tocar:**

| Doctype | Para qué |
|---|---|
| `Item` | Producto. Con `has_variants` para los que tienen presentaciones |
| `Item Attribute` | Talla, color, sabor, tamaño |
| `Item Variant` | Cada combinación vendible, con su propio código y stock |
| `Item Price` | Precio de venta por lista |
| `Bin` | Existencias reales por bodega |
| `Customer` / `Contact` / `Address` | El comprador y su dirección de envío |
| `Sales Order` | El pedido |
| `Sales Invoice` | La factura, cuando el cliente la necesite |
| `Payment Entry` | El pago registrado contra el pedido |
| `Shipping Rule` | Costo de envío por ciudad o por valor del pedido |

**Nuestros, en la app `antojate`:**

| Doctype | Para qué |
|---|---|
| `Wompi Settings` | Llaves de la pasarela (las privadas cifradas), modo sandbox/producción |
| `Wompi Transaction` | Bitácora de cada intento de pago y su estado final |
| `Antojate Settings` | Parámetros de la tienda: bodega, lista de precios, ciudades con envío |

Campos añadidos a doctypes de ERPNext (vía Custom Field, sin tocar el core):
visibilidad en la tienda, orden de aparición, galería de fotos y texto largo
del producto.

## 6. El recorrido de una compra

```
 1. El comprador navega el catálogo            → lee Item + Item Price + Bin
 2. Escoge variante (talla/color/sabor)        → valida stock disponible
 3. Agrega al carrito                          → carrito en la sesión, sin login
 4. Checkout: datos, dirección, ciudad         → calcula envío con Shipping Rule
 5. Confirma                                   → se crea el Sales Order en BORRADOR
 6. Se le manda a pagar a la pasarela          → Nequi / PSE / Bancolombia / tarjeta
 7. La pasarela avisa por webhook              → se valida la firma del evento
 8. Si el pago fue aprobado                    → Sales Order se confirma,
                                                 se crea el Payment Entry,
                                                 se descuenta el inventario,
                                                 se le manda correo al comprador
 9. Si fue rechazado                           → el borrador queda abandonado;
                                                 el comprador puede reintentar
10. El cliente despacha desde /desk             → Delivery Note y seguimiento
```

El inventario se compromete en el paso 8, no antes: ERPNext reserva cuando el
pedido se confirma, y el pedido solo se confirma cuando el pago entró. Un
checkout abandonado no deja rastro en el stock.

**El punto crítico es el 7.** La confirmación del pago *nunca* se cree porque el
navegador del comprador haya vuelto a la página de "gracias": esa URL se puede
falsificar escribiéndola a mano. El pedido solo se marca como pagado cuando llega
el webhook firmado desde el servidor de la pasarela y el checksum verifica. El
retorno del navegador sirve para mostrarle algo bonito al comprador, nada más.

## 7. Seguridad

- Las llaves privadas de la pasarela van en campos `Password` de Frappe, que se
  guardan cifrados. Nunca en el repositorio ni en el `.env`.
- El webhook valida el checksum firmado antes de tocar el pedido.
- El monto a cobrar se calcula **en el servidor** a partir del Sales Order. Nunca
  se confía en un total que venga del navegador: si no, cualquiera compra por $1.
- Cada intento de pago queda registrado en `Wompi Transaction`, para poder
  conciliar y para tener evidencia si hay una disputa.
- El webhook es idempotente: la pasarela reintenta, y procesar dos veces el mismo
  evento no puede cobrar ni descontar stock dos veces.

## 8. Plan de trabajo

| Fase | Entregable | Estado |
|---|---|---|
| 0 | Entorno local reproducible con un comando | hecho |
| 1 | App `antojate` instalada y sitio funcionando | hecho |
| 2 | Catálogo público: home, categoría, producto con variantes | hecho |
| 3 | Carrito y checkout, con cálculo de envío por ciudad | hecho |
| 4 | Integración de pagos + webhook firmado + pruebas | hecho |
| 5 | Datos de ejemplo y guía para el cliente | hecho |
| 6 | Afiliación a Wompi y llaves reales de sandbox | el cliente |
| 7 | Demo al cliente por túnel público | listo para hacerse |
| 8 | Fotos y catálogo real del cliente | pendiente |
| 9 | Correo de confirmación al comprador | pendiente |
| 10 | Paso a producción cuando haya presupuesto | pendiente |

Lo que quedó cubierto por pruebas automáticas (16, todas en verde):

- Las dos firmas de Wompi, incluida la reproducción exacta del ejemplo oficial
  de su documentación.
- Que el pedido nazca en borrador y solo el webhook lo confirme.
- Que un checksum inválido no toque el pedido.
- Que un monto que no cuadre no lo confirme.
- Que un evento repetido no cobre dos veces.
- Que el precio lo ponga el servidor.

## 9. Riesgos abiertos

| Riesgo | Mitigación |
|---|---|
| El cliente no afilia la pasarela a tiempo | Todo se desarrolla y demuestra en sandbox; cambiar a producción es cambiar cuatro llaves |
| La demo depende de que tu máquina esté encendida | Es aceptable para mostrar avances; se acuerda hora con el cliente |
| El cliente carga mal los productos | Guía con los tres requisitos para publicar (`03-guia-del-cliente.md`) |
| **Sobreventa en el último artículo** | Un borrador no reserva inventario en ERPNext: dos compradores pueden pasar la validación de stock a la vez y ambos pagar. La ventana es de minutos y solo afecta a la última unidad. Si llega a pasar, se resuelve reembolsando desde Wompi. Reservar de verdad exigiría confirmar el pedido antes de cobrar, que es peor: ensucia inventario y contabilidad con pedidos que nunca se pagan |
| Crece el catálogo y el portal Frappe se queda corto | El storefront está desacoplado del modelo de datos; se puede reemplazar sin tocar ERPNext |
