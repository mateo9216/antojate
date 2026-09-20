# Facturación electrónica ante la DIAN

**Estado: pendiente de construir.** Este documento existe para que, cuando haya
que facturar, nadie empiece de cero ni descubra tarde lo que falta.

Lo escribo ahora y no después por una razón: **el día que el cliente haga su
primera venta real, la obligación ya existe.** No es algo que se pueda dejar
para "cuando crezcamos".

---

## 1. Dónde estamos hoy

Esto no es una impresión: es lo que verifiqué en el sistema el 2026-09-19.

| | |
|---|---|
| Pedidos confirmados | Sí, se crean y se confirman solos con el pago |
| Pagos registrados | Sí, `Payment Entry` contra el pedido |
| **Facturas** | **Ninguna.** La palabra `Sales Invoice` no aparece en el código de la app |
| **IVA** | **No se calcula.** Ningún pedido tiene plantilla de impuestos aplicada |
| Identificación del comprador | **No se pide.** El checkout no captura cédula ni NIT |
| Localización colombiana de ERPNext | **No existe.** `regional/` trae Australia, Italia, Sudáfrica, Turquía, Emiratos y EE.UU. |
| Plan de cuentas colombiano | Sí, ERPNext lo trae y es el que usa el sitio |

Comprobé además que **sí funciona** generar una factura desde un pedido
confirmado con `make_sales_invoice()`: la creé, quedó con el total correcto y
la reverti sin dejar rastro. Pero esa factura **no tiene un solo campo de
DIAN**: ni CUFE, ni firma, ni nada.

O sea: la pieza contable existe y funciona. Lo que falta es todo lo electrónico.

---

## 2. Lo que hay que construir aunque no existiera la DIAN

Esto se pasa por alto porque todo el mundo se concentra en "conectarse con la
DIAN". Pero antes de eso hay tres cosas que dependen solo de nosotros, y sin
ellas ninguna integración sirve.

### 2.1 Calcular el IVA

Hoy el precio publicado se trata como monto final, sin desagregar impuesto.
Verificado en un pedido real: neto $76.000, impuestos $9.000, total $85.000 —
y esos $9.000 **son el envío**, no IVA.

Una factura tiene que mostrar la base gravable y el impuesto por separado. Eso
exige:

- Decidir con el cliente si los precios publicados **ya incluyen IVA** (lo
  normal en Colombia: el comprador espera ver el precio final) o si se suma en
  el checkout.
- Aplicar la plantilla de impuestos al pedido según la tarifa de cada producto.
  No todo lleva 19%: hay productos al 5% y exentos, y en un catálogo mixto
  conviven varias tarifas.
- Configurar la tarifa **por producto**, no global.

**Esta es la decisión de negocio que hay que tomar primero**, porque cambia los
precios que se publican.

### 2.2 Crear la factura

Hoy el pago confirma el pedido y registra el ingreso, pero no factura. Hay que
decidir cuándo nace la factura:

- **Al confirmarse el pago** — el comprador la recibe de inmediato. Es lo que
  espera quien compra por internet.
- **Al despachar** — se factura lo que realmente salió. Más prudente si hay
  riesgo de quiebres de stock o cancelaciones.

Son dos comportamientos distintos del negocio, no dos formas de programarlo.

### 2.3 Pedir la identificación del comprador

El checkout pide nombre, correo, celular, ciudad y dirección. **No pide
documento de identidad**, y una factura electrónica nominal lo necesita.

Hay que agregar al checkout tipo y número de documento, y decidir qué pasa con
quien no lo quiera dar. Cada campo que se agrega al checkout cuesta ventas, así
que la decisión no es solo técnica.

---

## 3. Qué exige la norma

Verificado contra el micrositio oficial de la DIAN (septiembre de 2026).

### Quién está obligado

> «Las personas o empresas que venden bienes o prestan servicios deberán
> expedir factura», «a excepción de las que por expresa disposición legal no
> están obligadas a expedir factura».

El fundamento es el **artículo 615 del Estatuto Tributario** y el **artículo
1.6.1.4.1 del Decreto Único Reglamentario 1625 de 2016**.

La regla general, entonces, es que **hay que facturar**. Las excepciones son
taxativas y **no las va a determinar este documento**: las confirma el contador
del cliente según su régimen. La DIAN también contempla el caso de quien no
está obligado pero quiere facturar electrónicamente de forma voluntaria, y en
ese caso sigue el mismo proceso.

### Qué documento se emite

El sistema de facturación electrónica abarca la factura electrónica de venta,
los documentos equivalentes electrónicos, las notas crédito y débito, el
documento soporte y el RADIAN.

Para esta tienda hay dos que importan:

- **Factura electrónica de venta.** Es la que corresponde a una venta a
  distancia con datos del comprador.
- **Nota crédito electrónica.** Es la que se emite cuando hay que anular o
  devolver. **Y esto sí es seguro que va a pasar**: el derecho de retracto de
  la Ley 1480 da 5 días hábiles al comprador en ventas a distancia. Una tienda
  en línea necesita notas crédito desde el primer mes.

Los **documentos equivalentes** (entre ellos el tiquete POS) están regulados
por la **Resolución 000165 de 2023**, y el micrositio aclara que el tiquete POS
«se podrá realizar independientemente del valor de la operación». Aun así,
están pensados para venta presencial. **Que apliquen o no a una venta por
internet es justamente una de las preguntas para el contador**, no algo que
debamos asumir.

### Sin habilitarse no se factura

No basta con generar un XML. Hay que quedar **habilitado** ante la DIAN, y el
proceso tiene siete pasos:

1. Actualizar el RUT, tener software de facturación y certificado de firma
   digital.
2. Registrarse en el portal de factura electrónica.
3. Informar el **modo de operación**: con qué software se va a facturar.
4. **Set de pruebas**: la DIAN entrega rangos de numeración de prueba y hay que
   enviarle facturas de ensayo «hasta obtener el estado de habilitado».
5. Indicar la fecha de inicio en producción.
6. Solicitar los rangos de numeración reales en MUISCA.
7. Asociar los prefijos en el portal.

El paso 4 es el que se subestima siempre: **el software tiene que pasar un set
de pruebas contra la DIAN antes de poder emitir una sola factura real.**

---

## 4. Cómo funciona por dentro

La DIAN trabaja con **validación previa**: la factura no es válida cuando la
emitimos, sino cuando la DIAN la valida. El flujo es:

```
  Factura en ERPNext
        ↓
  Se genera el XML en formato UBL 2.1 (OASIS)
        ↓
  Se firma digitalmente con el certificado del comercio
        ↓
  Se envía a la DIAN por sus servicios web
        ↓
  La DIAN valida y devuelve el CUFE
        ↓
  Se entrega al comprador: XML + representación gráfica (PDF con QR)
```

La documentación técnica oficial que haría falta para construir esto:

| Recurso | Para qué |
|---|---|
| [Anexo Técnico Factura Electrónica de Venta v1.9](https://www.dian.gov.co/impuestos/factura-electronica/Documents/Anexo-Tecnico-Factura-Electronica-de-Venta-vr-1-9.pdf) | La especificación completa. Es el documento de referencia |
| [Caja de herramientas FE v1.9](https://www.dian.gov.co/impuestos/factura-electronica/Documents/Caja-de-herramientas-FE_V19_v2026.zip) | Ejemplos, esquemas y utilidades que publica la DIAN |
| [Guía para el consumo de Web Services](https://www.dian.gov.co/impuestos/factura-electronica/Documents/Guia-Herramienta-para-el-Consumo-de-Web-Services.pdf) | Cómo hablarle a la DIAN |
| [OASIS UBL 2.1](http://docs.oasis-open.org/ubl/os-UBL-2.1/xsdrt/maindoc/) | El estándar del XML |

Que el anexo técnico vaya en la versión 1.9 dice algo importante: **esto cambia
con el tiempo**. Lo que se construya hay que mantenerlo cuando la DIAN publique
una versión nueva.

---

## 5. Las tres rutas

La DIAN misma reconoce tres formas de facturar: su solución gratuita, un
proveedor tecnológico autorizado, o software propio.

### Ruta A — La solución gratuita de la DIAN

**Qué es.** Software gratuito «para todos los empresarios y responsables que
deseen cumplir con la obligación de facturar electrónicamente», **sin límite de
volumen**, e incluye el **certificado de firma digital gratis con vigencia de
dos años**.

**El problema.** Es una herramienta web: se entra, se llenan los datos y se
emite. **La DIAN no documenta ninguna API para integrarse desde otro sistema.**

Para esta tienda eso significa que alguien tendría que **copiar a mano** cada
pedido de ERPNext al portal de la DIAN. Con cinco pedidos al día es tedioso
pero viable; con cincuenta es imposible y además se van a cometer errores.

- **Desarrollo:** ninguno.
- **Costo:** $0.
- **Costo real:** el tiempo de una persona, todos los días, para siempre.

### Ruta B — Un proveedor tecnológico por API

**Qué es.** Hay **97 proveedores tecnológicos autorizados** por la DIAN, con
catálogo público. Varios ofrecen API REST: nosotros les mandamos los datos de
la factura y ellos se encargan del UBL, la firma, el envío a la DIAN y el PDF
con QR.

**Lo que nos tocaría construir:** tomar el `Sales Invoice` de ERPNext,
convertirlo al formato del proveedor, manejar la respuesta, guardar el CUFE y
el estado, adjuntar el XML y el PDF, mandárselos al comprador, y cubrir las
notas crédito.

- **Desarrollo estimado:** de 5 a 10 días-persona. Es una estimación, no una
  cotización: depende de qué tan buena sea la API del proveedor que se elija.
- **Costo recurrente:** el plan del proveedor, normalmente por documento o por
  paquete mensual.
- **Ventaja de fondo:** cuando la DIAN cambie el anexo técnico, **el problema
  es del proveedor**, no nuestro.

### Ruta C — Software propio, hablando directo con la DIAN

**Qué es.** Construir nosotros el UBL 2.1, la firma digital, el consumo de los
servicios web, el CUFE, la representación gráfica y pasar el set de pruebas.

**Por qué no la recomiendo para este cliente.** Como referencia de tamaño: la
localización italiana de ERPNext —el caso más parecido que existe en el código,
también XML enviado a un ente estatal— pesa unas **1.400 líneas**, y ni
siquiera resuelve la firma ni el envío directo. Sumale el set de pruebas de
habilitación y el mantenimiento perpetuo cada vez que salga una versión nueva
del anexo técnico.

- **Desarrollo estimado:** de 25 a 40 días-persona, más mantenimiento continuo.
- **Costo recurrente:** solo el certificado de firma.
- **Cuándo tendría sentido:** con un volumen tan alto que el costo por documento
  del proveedor supere lo que cuesta mantener el desarrollo. No es el caso de
  una tienda que arranca.

---

## 6. Recomendación

**Ruta B: un proveedor tecnológico por API.**

Es el único punto donde el esfuerzo de desarrollo es razonable *y* la operación
no depende de que alguien transcriba pedidos a mano *y* el mantenimiento
normativo no queda de nuestro lado.

Con una salvedad honesta: **si el cliente va a vender muy poco al principio
—menos de unos pocos pedidos por día—, la ruta A es una decisión sensata para
arrancar.** Facturar a mano mientras el volumen es bajo permite salir a vender
sin esperar un desarrollo, y la migración a la ruta B después no tira nada a la
basura, porque el trabajo de la sección 2 (IVA, factura, identificación del
comprador) hay que hacerlo igual en los dos casos.

Lo que **no** recomiendo es quedarse en la ruta A sin fecha de salida. Funciona
hasta que deja de funcionar, y suele dejar de funcionar justo cuando al negocio
le empieza a ir bien.

---

## 7. Qué hay que decidir con el cliente

Preguntas concretas, para hacérselas de una y no en cuentagotas:

1. **¿Cuál es el régimen del negocio?** ¿Persona natural o jurídica?
   ¿Responsable de IVA? De esto depende toda la obligación.
2. **¿Ya factura hoy, por fuera de la tienda?** Si tiene contador o un software
   contable andando, puede que lo más barato sea conectarse con lo que ya usa.
3. **¿Los precios publicados incluyen IVA?**
4. **¿Qué tarifa de IVA lleva cada producto?**
5. **¿Cuántas facturas al mes espera?** Es la pregunta que decide entre la
   ruta A y la B.
6. **¿La factura se emite al pagar o al despachar?**
7. **¿Quién responde ante la DIAN?** El cliente. Nosotros construimos la
   herramienta, pero la obligación tributaria es suya, y conviene que quede
   por escrito.

---

## 8. Plan de trabajo, si se aprueba

**Fase 1 — Lo que hay que hacer en cualquier caso** (sección 2)

1. Definir con el cliente el tratamiento del IVA y aplicarlo por producto.
2. Agregar tipo y número de documento al checkout.
3. Generar el `Sales Invoice` automáticamente en el momento que se acuerde.
4. Ajustar las pruebas para cubrir todo lo anterior.

**Fase 2 — Escoger e integrar**

5. Escoger proveedor del catálogo de la DIAN, comparando API, sandbox y precio.
6. Construir la integración: envío, CUFE, estados, reintentos.
7. Notas crédito para devoluciones y retracto.
8. Entrega al comprador: XML y PDF con QR por correo.

**Fase 3 — Habilitación y salida**

9. Acompañar al cliente en los siete pasos de habilitación.
10. Pasar el set de pruebas contra la DIAN.
11. Emitir **una factura real** y verificarla de punta a punta, igual que se
    hizo con el primer pago real.

La fase 3 depende de trámites del cliente, no de nosotros. Conviene arrancarla
en paralelo con la fase 1, no después.

---

## 9. Lo que falta verificar

Para ser honestos sobre los límites de este documento:

- **Las apps de la comunidad Frappe para Colombia no las pude revisar.** Se
  acabó el presupuesto de búsquedas web de la sesión. Antes de escribir código
  hay que mirar si alguien ya resolvió esto y en qué estado está; podría
  cambiar la estimación de la ruta B. Lo que **sí** verifiqué es que **ERPNext
  no trae nada de Colombia de fábrica**.
- **Los precios de los proveedores tecnológicos** hay que cotizarlos. Los 97
  autorizados están en el catálogo público de la DIAN.
- **Si a esta tienda le sirve un documento equivalente** en vez de factura
  electrónica de venta: es pregunta para el contador.

## 10. Lo que este documento NO es

**No es asesoría tributaria ni legal.** Es el análisis técnico de un equipo de
desarrollo sobre qué hay que construir. Las obligaciones concretas del negocio
—si está obligado, desde cuándo, bajo qué régimen— las confirma el contador del
cliente.

Lo que sí afirmamos con certeza es la sección 1: qué hace y qué no hace hoy el
sistema.

---

**Fuentes** (consultadas el 2026-09-19)

- [Sistema de facturación electrónica — DIAN](https://micrositios.dian.gov.co/sistema-de-facturacion-electronica/)
- [¿Debes facturar electrónicamente?](https://micrositios.dian.gov.co/sistema-de-facturacion-electronica/debes-facturar-electronicamente/)
- [Pasos para ser facturador electrónico](https://micrositios.dian.gov.co/sistema-de-facturacion-electronica/preparate-pasos-para-ser-facturador-electronico/)
- [Facturación gratuita DIAN](https://micrositios.dian.gov.co/sistema-de-facturacion-electronica/facturacion-gratuita-dian/)
- [Documento equivalente electrónico](https://micrositios.dian.gov.co/sistema-de-facturacion-electronica/documento-equivalente-electronico/)
- [Proveedores tecnológicos y catálogo de participantes](https://micrositios.dian.gov.co/sistema-de-facturacion-electronica/proveedores-tecnologicos/)
- [Documentación técnica](https://micrositios.dian.gov.co/sistema-de-facturacion-electronica/documentacion-tecnica/)
