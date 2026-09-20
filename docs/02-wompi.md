# Cobros con Wompi

## Por qué Wompi

Se compararon Wompi, Bold, ePayco, PayU/Rapyd y Mercado Pago contra la
documentación oficial vigente. Wompi gana con margen claro para este caso:

| | Wompi | Bold | ePayco | PayU/Rapyd | Mercado Pago |
|---|---|---|---|---|---|
| Nequi | sí, nativo | sí | no documentado | sí | **no lo soporta** |
| Botón Bancolombia | sí, + Transfer y QR | sí | sí | sí | no |
| PSE | sí | sí | sí | sí | sí |
| Tarifa (antes de IVA) | **2,65% + $700** | 2,89% + $900 | 2,64%-3,29% + ~$700 | 3,29% + $300 | 2,79%-3,29% + $800 |
| Llaves de prueba | **al instante, self-service** | requieren aprobación manual | sí | sí | sí |
| Dispersión | siguiente día hábil | día siguiente | 24-72 h | hasta 3 días, bajo solicitud | 1-2 días tras liberación |

Lo decisivo: es la única con **Nequi + todos los canales de Bancolombia + la
tarifa más baja + registro inmediato sin comité comercial**. Mercado Pago quedó
descartado porque no soporta Nequi en Colombia, que era requisito.

### Costo real, con IVA incluido

| Venta | Se queda Wompi | Efectivo |
|---|---|---|
| $30.000 | $1.779 | 5,9% |
| $100.000 | $3.986 | 4,0% |
| $300.000 | $10.294 | 3,4% |
| $1.000.000 | $32.368 | 3,2% |

## Dos advertencias antes de que el cliente se afilie

1. **Persona natural: el primer desembolso llega 30 días después de la primera
   venta**, y exige cuenta Bancolombia con más de 30 días de antigüedad. Si el
   negocio necesita la plata antes, hay que afiliarse como persona jurídica o
   contar con ese colchón. Conviene decírselo al cliente ahora, no después.
2. **No hay SDK oficial** de Wompi para ningún lenguaje. La integración de este
   proyecto habla con su API REST directamente, que es sencilla y está bien
   documentada. Los paquetes de terceros en npm tienen ~100 descargas al mes y
   no se recomiendan.

## Qué necesita el cliente para afiliarse

Registro en **https://comercios.wompi.co**.

**Persona natural**
- [ ] Cédula del titular
- [ ] RUT
- [ ] Cuenta **Bancolombia** a su nombre, con más de 30 días de abierta
- [ ] *No* se exige cámara de comercio

**Persona jurídica**
- [ ] NIT y RUT
- [ ] Cámara de comercio (vigencia reciente)
- [ ] Cédula del representante legal
- [ ] Certificación bancaria de la cuenta del negocio

## Mientras tanto: sandbox, gratis y hoy

No hay que esperar la afiliación para tener todo funcionando. El sandbox se
obtiene al instante registrándose en comercios.wompi.co y entrando al ambiente
de pruebas. No mueve dinero real.

### Las cuatro llaves

En el panel: **Desarrolladores → Secretos para integración técnica**.

| Llave | Prefijo en pruebas | Prefijo en producción | Para qué |
|---|---|---|---|
| Pública | `pub_test_` | `pub_prod_` | Identifica el comercio, viaja al navegador |
| Privada | `prv_test_` | `prv_prod_` | Consultar transacciones desde el servidor |
| Integridad | `test_integrity_` | `prod_integrity_` | Firmar el monto del checkout |
| Eventos | `test_events_` | `prod_events_` | Validar que el webhook es auténtico |

### Cargarlas

En el escritorio: **Wompi Settings**. Pegá las cuatro en el bloque de pruebas,
dejá *Ambiente* en `Sandbox` y marcá *Cobros en línea activos*.

Las privadas se guardan cifradas en la base de datos. **No van al repositorio
ni al archivo `.env`.**

### Configurar el webhook

Wompi necesita una URL pública a la que avisar. Con el túnel andando
(`./scripts/tunnel.sh`), cargá en el panel de Wompi como URL de eventos:

```
https://<lo-que-diga-el-tunel>.trycloudflare.com/api/method/antojate.api.pagos.webhook_wompi
```

Hay que actualizarla cada vez que reinicies el túnel, porque la URL cambia.

### Datos para probar en sandbox

Estos los publica Wompi en su documentación de pruebas. Verificalos contra la
página oficial antes de depender de ellos: fueron tomados de la documentación,
no probados contra el sandbox real todavía.

| Medio | Aprueba | Rechaza |
|---|---|---|
| Tarjeta | `4242 4242 4242 4242` | `4111 1111 1111 1111` |
| Nequi | `3991111111` | `3992222222` |
| PSE | banco código `1` | banco código `2` |

## Cómo está construida la integración

### El cobro

1. El comprador confirma el checkout.
2. El servidor crea el `Sales Order` **en borrador** y un `Wompi Transaction`
   con una referencia única.
3. Firma el monto: `SHA256(referencia + monto_en_centavos + moneda + secreto)`.
4. Manda al comprador al Checkout Web de Wompi con esa firma.

El monto sale del pedido, calculado en el servidor. La firma impide que alguien
edite el total en la URL: cambiarlo invalida la firma y Wompi rechaza el cobro.

### La confirmación

Wompi envía un `POST` a nuestro webhook con el evento `transaction.updated`.
El endpoint:

1. Recalcula el checksum: concatena los valores de los campos que el propio
   evento lista en `signature.properties`, más el `timestamp`, más el secreto
   de eventos, y lo compara en tiempo constante.
2. Verifica que el monto pagado coincida con el del pedido.
3. Confirma el pedido, descuenta el inventario y crea el `Payment Entry`.
4. Marca la transacción como procesada, para que un reintento no la aplique
   dos veces.

**El regreso del comprador al sitio no confirma nada.** Esa URL se escribe a
mano en la barra de direcciones; el webhook firmado, no. Si algún día alguien
"arregla" esto confiando en el redirect, la tienda queda regalando productos.

Wompi reintenta hasta 3 veces en 24 horas (a los 30 min, 3 h y 24 h) hasta
recibir un HTTP 200.

### Estados posibles

`PENDING` → `APPROVED` | `DECLINED` | `VOIDED` | `ERROR`. Los últimos cuatro
son finales. Ningún medio de pago responde de forma síncrona: siempre se espera
el webhook.

## Pasar a producción

1. Cargar las cuatro llaves `*_prod_*` en el bloque de producción.
2. Cambiar *Ambiente* a `Producción`.
3. Actualizar la URL del webhook en el panel de Wompi al dominio real.
4. Hacer **una compra de verdad, con plata real**, por el monto más bajo
   posible, y confirmar que el pedido queda confirmado y el `Payment Entry`
   creado. Un sandbox verde no garantiza que producción funcione.

## Referencias

- https://docs.wompi.co/docs/colombia/ambientes-y-llaves/
- https://docs.wompi.co/docs/colombia/widget-checkout-web/
- https://docs.wompi.co/docs/colombia/eventos/
- https://docs.wompi.co/docs/colombia/transacciones/
- https://docs.wompi.co/docs/colombia/datos-de-prueba-en-sandbox/
