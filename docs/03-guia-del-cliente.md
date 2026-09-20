# Guía para administrar la tienda

Para la persona que va a cargar los productos y despachar los pedidos.
No hay que saber programar.

Se entra en **http://antojate.localhost:8080/desk** (o el dominio que tenga la
tienda cuando esté publicada).

## 1. Crear una categoría

Buscá **Item Group** (Grupo de artículos) → *Add Item Group*.

1. Nombre de la categoría: por ejemplo `Postres`.
2. *Parent Item Group*: `All Item Groups`.
3. Marcá **Mostrar como categoría en la tienda**.
4. *Orden de la categoría*: número más bajo, aparece más a la izquierda.

Sin marcar esa casilla, la categoría no sale en el menú de la tienda.

## 2. Crear un producto sencillo

Buscá **Item** (Artículo) → *Add Item*.

| Campo | Qué poner |
|---|---|
| Item Code | Un código corto y único: `BROWNIE-6` |
| Item Name | El nombre que ve el comprador |
| Item Group | La categoría |
| Image | La foto. Cuadrada se ve mejor (800×800 está bien) |
| Maintain Stock | Marcado, si querés controlar existencias |

Bajá hasta **Tienda en línea** y marcá **Publicar en la tienda**. Ahí mismo:

- **Destacado en la portada**: lo sube al principio del catálogo.
- **Orden de aparición**: número más bajo aparece primero. Dejalo en 999 si no
  te importa.
- **Descripción para la tienda**: lo que lee el comprador en la ficha.

### El precio

El producto no aparece en la tienda si no tiene precio.

Buscá **Item Price** → *Add Item Price*:

- *Item Code*: el producto
- *Price List*: `Standard Selling`
- *Rate*: el precio de venta

### Las existencias

Para que se pueda comprar tiene que haber unidades en la bodega.

Buscá **Stock Entry** → *Add Stock Entry*:

- *Stock Entry Type*: `Material Receipt`
- En la tabla: el producto, la cantidad, y *Target Warehouse* = la bodega de la
  tienda
- Guardá y dale **Submit**

Un producto sin existencias se muestra como **Agotado** y no se puede comprar.

## 3. Crear un producto con variantes

Variantes son las presentaciones de un mismo producto: tallas, colores,
sabores. Cada una tiene su propio precio y sus propias existencias.

**Primero el atributo.** Buscá **Item Attribute** → *Add*:

- *Attribute Name*: `Talla`
- En la tabla, los valores: `S`, `M`, `L`

**Después el producto plantilla.** Creá el Item normalmente, y además:

1. Marcá **Has Variants**.
2. En la tabla *Attributes*, agregá `Talla`.
3. Marcá **Publicar en la tienda**.

**Por último las variantes.** Desde el producto plantilla, botón
*Create → Variant*. Se crea un Item por cada talla.

A cada variante hay que ponerle **su propio precio y sus propias existencias**,
igual que a un producto sencillo. Marcá también *Publicar en la tienda* en cada
una.

En la tienda el comprador ve un solo producto, con botones para escoger la
talla. Las que estén agotadas aparecen tachadas y no se pueden escoger.

## 4. Ciudades de envío

Buscá **Antojate Ciudad Envio**.

| Campo | Qué significa |
|---|---|
| Ciudad | Como la va a ver el comprador |
| Costo del envío | Lo que se le suma al pedido |
| Días hábiles de entrega | Se le muestra en el checkout |
| Envío gratis desde | Si el pedido supera este valor, no se cobra envío. 0 = nunca |
| Se envía a esta ciudad | Desmarcala para dejar de vender ahí sin borrar nada |

**Una ciudad que no esté en esta lista no puede comprar.** Si un cliente se
queja de que no puede terminar el pedido, esto es lo primero que hay que mirar.

## 5. Los pedidos que van llegando

Buscá **Sales Order** (Pedido de venta).

| Estado | Qué significa |
|---|---|
| **Draft** (borrador) | El comprador llegó al pago pero todavía no pagó |
| **To Deliver and Bill** | **Pagó.** Hay que despacharlo |
| **Completed** | Entregado |

Los pedidos en borrador con varias horas son carritos abandonados. Es normal
que haya: no todo el que llega al pago termina pagando.

### Despachar

Abrí el pedido pagado y usá **Create → Delivery Note**. Eso descuenta el
inventario y deja registro de la entrega.

La dirección de envío está en el pedido, y el celular del comprador también.

### Ver los pagos

Buscá **Wompi Transaction**. Cada intento de pago queda ahí con su estado:

- `APPROVED` — entró la plata
- `DECLINED` — el banco lo rechazó
- `PENDING` — todavía se está procesando
- `ERROR` / `VOIDED` — no se completó

Si un comprador dice que pagó y el pedido sigue en borrador, buscá su pedido
acá y mirá el estado del último intento.

## Preguntas que van a salir

**«Subí el producto y no aparece en la tienda.»**
Repasá las tres condiciones: marcado *Publicar en la tienda*, tiene precio en
`Standard Selling`, y tiene existencias. Falta una de las tres casi siempre.

**«El cliente dice que pagó pero no me llegó el pedido.»**
Mirá **Wompi Transaction**. Si dice `APPROVED` y el pedido sigue en borrador,
avisale al equipo técnico: el aviso de Wompi no llegó y hay que revisarlo.
Si dice `DECLINED`, el pago no entró: que lo intente otra vez.

**«Quiero dejar de vender algo por un tiempo.»**
Desmarcá *Publicar en la tienda*. No lo borres: si lo borrás perdés el
histórico de lo que ya se vendió.
