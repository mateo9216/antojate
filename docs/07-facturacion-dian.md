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
| Localización colombiana de ERPNext | **No existe, ni en el core ni en la comunidad** (ver abajo) |
| Plan de cuentas colombiano | Sí, ERPNext lo trae y es el que usa el sitio |

Comprobé además que **sí funciona** generar una factura desde un pedido
confirmado con `make_sales_invoice()`: la creé, quedó con el total correcto y
la reverti sin dejar rastro. Pero esa factura **no tiene un solo campo de
DIAN**: ni CUFE, ni firma, ni nada.

O sea: la pieza contable existe y funciona. Lo que falta es todo lo electrónico.

### No hay nada hecho para Colombia

Vale la pena detenerse acá, porque la primera reacción de cualquiera es "algo
debe haber". Se revisó por cuatro vías independientes y no lo hay:

- El core de ERPNext v16 trae localización para Australia, Italia, Sudáfrica,
  Turquía, Emiratos y Estados Unidos. **Colombia no está.**
- El marketplace de Frappe Cloud tiene apps de cumplimiento para México,
  Argentina, Egipto, Arabia Saudita, Malasia, Kenia, India y Emiratos.
  **Ninguna para Colombia.**
- Las búsquedas en GitHub devuelven un solo repositorio colombiano para Frappe,
  y **no sirve**: gestiona documentos normativos, no factura.
- Tampoco existe un marco genérico de facturación electrónica en el core sobre
  el cual apoyarse. Cada país se construye entero.

Conclusión práctica: **no hay atajo por ese lado, y no conviene esperar a que
aparezca.**

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

**Una trampa concreta:** la plantilla de impuestos para Colombia que trae
ERPNext (`country_wise_tax.json`) dice **16%**, que es la tarifa que estuvo
vigente hasta 2016. Hoy la general es 19%. Si alguien la aplica sin mirar,
factura mal desde el primer día.

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
por la **Resolución 000165 de 2023** —que derogó la 000042 de 2020, así que si
alguien te pasa documentación citando esa última, está desactualizada. Y una
precisión más: ese articulado fue compilado en la **Resolución Única 000227 del
23 de septiembre de 2025**, así que hoy lo correcto es citar los artículos
`1.5.1.x`, no la resolución original—, y el micrositio aclara que el tiquete POS
«se podrá realizar independientemente del valor de la operación». Aun así,
están pensados para venta presencial. **Que apliquen o no a una venta por
internet es justamente una de las preguntas para el contador**, no algo que
debamos asumir.

### El certificado de firma digital

Una factura electrónica va firmada digitalmente, y ese certificado no lo emite
cualquiera: tiene que venir de una **Entidad de Certificación Digital
acreditada por el ONAC**. El directorio público de acreditados está en
[onac.org.co/directorio-de-acreditados](https://onac.org.co/directorio-de-acreditados/),
buscando por el esquema ECD. Ahí hay que consultarlo en el momento de decidir:
la lista cambia, hay entidades que entran, se suspenden o se retiran.

Dos cosas prácticas sobre el costo:

- **Por la ruta gratuita de la DIAN el certificado no cuesta nada.** La propia
  DIAN lo dice: se solicita sin costo, con vigencia de dos años y trámite
  completamente virtual. Es el argumento más fuerte de esa ruta.
- **Por fuera de ahí, no hay precios de lista públicos.** Se revisaron los
  sitios de varias entidades acreditadas y ninguna publica tarifas: todas
  remiten a cotización. Circula por blogs una cifra de $120.000-$180.000 al
  año, pero es estimación de un tercero y además contradice la vigencia de dos
  años que sí está documentada. **No la uses para costear: pedí cotización.**

Si se va por un proveedor tecnológico, vale preguntarle si el certificado va
incluido en el plan. Alegra dice que sí; con los demás hay que confirmarlo,
porque es un costo que aparece después si nadie preguntó antes.

### Tres detalles que se preguntan siempre

- **La resolución de numeración dura máximo dos años** y no puede pedirse por
  menos. Si el rango se agota, se pide otro. Si va a vencer con rango sin usar,
  la solicitud se tramita **hasta 15 días hábiles antes** del vencimiento.
  Conviene ponerlo en el calendario: quedarse sin numeración es quedarse sin
  poder vender.
- **El RADIAN no aplica** a esta tienda. Es el registro de facturas como título
  valor, para quien las negocia. Si el cliente no va a vender sus facturas, no
  le corresponde.
- **El tiquete POS electrónico ya es obligatorio para todos**, con un umbral de
  5 UVT (unos $261.870 con la UVT de 2026, $52.374). No le aplica a una tienda
  en línea que factura, **pero sí el día que el cliente abra un punto físico**.

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

**Esto condiciona el diseño, no es un detalle.** No hay un plazo de gracia para
enviar la factura después: la factura **no existe** hasta que la DIAN la valida.
Las únicas ventanas diferidas son de 48 horas y solo aplican en contingencia.

Consecuencias concretas para la tienda:

- La emisión tiene que ser **síncrona, o con reintentos en segundo plano** y
  visibilidad del estado. No sirve un "lo mando después".
- **Al comprador no se le puede entregar nada antes de que la DIAN valide.**
  El correo de "acá está tu factura" sale después de la validación, no antes.

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

La DIAN reconoce tres formas de facturar: su solución gratuita, un proveedor
tecnológico autorizado, o software propio habilitado.

### Antes de comparar: quién queda como responsable

Es la distinción que más pesa y la que casi nadie explica.

- **Proveedor tecnológico (PT) habilitado.** La DIAN mantiene un registro
  público de proveedores autorizados —97 en la última revisión—. Si se contrata
  a uno de ellos, el comercio **opera amparado bajo la habilitación del
  proveedor**.
- **Software propio.** Si el proveedor **no** está en ese registro, lo que se
  está usando es la modalidad de software propio: **el cliente se habilita ante
  la DIAN y es el titular responsable**.

Ninguna de las dos es ilegal. Pero cambian quién responde, y cambian el trámite
que le toca al cliente. **Preguntale a cualquier proveedor, por escrito, bajo
qué habilitación transmite**, y contrastalo contra el catálogo oficial de la
DIAN antes de firmar. Hay proveedores conocidos y con buena API que **no** están
en ese registro.

### Ruta A — La solución gratuita de la DIAN

**Qué es.** Software gratuito de la propia DIAN. Y es mejor de lo que suele
suponerse:

- **No tiene topes.** La norma es explícita: puede usarse «sin atender límite
  de cantidad, montos de los documentos, adquirentes, bienes y/o servicios».
  Cualquiera que te diga que hay un límite en UVT o en número de facturas,
  está equivocado.
- **El certificado de firma digital es gratis** por esta vía, con vigencia de
  dos años y trámite virtual.

**El problema.** Es una herramienta web, con carga por plantillas. **No tiene
API.** Alguien tendría que pasar cada pedido a mano.

- **Desarrollo:** ninguno. Con un reporte de pedidos listos para facturar,
  1-3 días-persona.
- **Costo:** **$0 al año**, certificado incluido.
- **Costo real:** el tiempo de una persona, por cada pedido.

### Ruta B — Un proveedor tecnológico por API

**Qué es.** Le mandamos los datos de la factura en JSON y el proveedor arma el
UBL, lo firma, lo transmite a la DIAN y devuelve el CUFE, el XML y el PDF.
**Nosotros no tocamos XML.**

Del relevamiento, lo que hay que saber antes de elegir:

| | Estado en el registro DIAN | API | Precio |
|---|---|---|---|
| **Alegra** | Habilitado | REST, producto *e-provider*, con sandbox | **No publicado** para la API |
| **The Factory HKA** | Habilitado | REST con Swagger abierto, y SOAP | No publicado |
| **Cadena** | Habilitado | No documentada públicamente | Publicado, desde ~$30.900/mes |
| **Factus** | **No aparece** | REST, sandbox gratuito, muy buena documentación | No publicado |

Dos advertencias que salieron del contraste y que conviene tener presentes:

- **El precio bajo que Alegra publica (~$17.900/mes) es el de su aplicación
  manual, no el de la API.** El producto para integrar es otro y su precio no
  está publicado. Es un error fácil de cometer al costear.
- **Factus no aparece en el registro oficial de proveedores**, lo que sugiere
  modalidad de software propio. No lo descarta —su API es la más cómoda del
  lote y su sandbox es abierto—, pero **hay que preguntárselo antes**.

**Lo que nos tocaría construir:**

| Pieza | Días-persona |
|---|---|
| Doctype de configuración + autenticación con reintentos | 2 |
| Armar el payload y mapear los catálogos de la DIAN (tipo de documento, DIVIPOLA, unidades, tributos, formas de pago) | 3-5 |
| Envío al confirmar la factura, en segundo plano, con estados y errores | 2-3 |
| Guardar CUFE, XML y PDF; formato de impresión con QR; envío por correo | 2-3 |
| Notas crédito para anulaciones y devoluciones | 2 |
| Pruebas en sandbox y acompañar el set de pruebas de habilitación | 2-4 |
| **Integración** | **13-20** |
| **Más el trabajo previo de la sección 2** | **+4-7** |
| **Total** | **17-27 días-persona** |

Donde se va el tiempo real no es en hablar con la API: es en **el mapeo de los
catálogos de la DIAN**, con campos obligatorios condicionales según el tipo de
operación.

A favor: el equipo ya tiene el patrón construido. `api/pagos.py`, con su doctype
de configuración, sus llaves cifradas y su manejo de estados, es exactamente
esta forma. No es territorio nuevo.

**Una salvaguarda barata:** meter la llamada al proveedor detrás de una interfaz
mínima —un solo método `emitir(factura)`—. Con varios candidatos vivos y la
mitad sin precio público, vale más que nunca: cambiar de proveedor no debería
ser reescribir la integración.

### Ruta C — Software propio, hablando directo con la DIAN

**Qué es.** Construir nosotros el UBL 2.1, la firma digital, el consumo de los
servicios web, el CUFE, la representación gráfica y pasar el set de pruebas.

**Es técnicamente posible en este stack.** Se verificó que las librerías
necesarias funcionan en Python 3.14: `xmlsec` publica ruedas `cp314` y
`signxml` trae el firmador XAdES que exige la DIAN.

**Pero el ecosistema del que uno se apoyaría es frágil.** La librería histórica
de Python para esto, `facho`, está **archivada**. Lo más completo que existe
hoy es un proyecto en TypeScript de un solo autor —lo que obligaría a montar un
contenedor de Node al lado— y el resto son repositorios sin tracción.
Construir sobre eso es heredar el mantenimiento de todo.

Como referencia de tamaño: la localización italiana de ERPNext —el caso más
parecido en el propio código, también XML enviado a un ente estatal— pesa unas
**1.400 líneas**, y ni siquiera resuelve la firma ni el envío.

- **Desarrollo estimado:** de 40 a 60 días-persona, más mantenimiento continuo.
- **Cuándo tendría sentido:** con un volumen tan alto que el costo por documento
  del proveedor supere lo que cuesta mantener el desarrollo. No es el caso de
  una tienda que arranca.

## 6. Recomendación

**Cambié de opinión sobre el orden.** La primera versión de este documento
recomendaba integrar un proveedor desde el arranque y usar la herramienta
gratuita apenas como puente incómodo. Al verificar que **la solución gratuita
de la DIAN no tiene topes de volumen y entrega el certificado de firma gratis**,
esa herramienta deja de ser un parche y pasa a ser un punto de partida legítimo.

**1. Ahora, sin esperar a nadie: el trabajo previo (4-7 días-persona).**
IVA por producto, decidir si los precios publicados lo incluyen, capturar el
documento de identidad en el checkout y generar la factura al confirmarse el
pago. Hay que hacerlo en cualquier escenario y **bloquea todo lo demás**. La
decisión sobre el IVA cambia los precios que se publican: cuanto antes, mejor.

**2. Arrancar con la solución gratuita de la DIAN (1-3 días-persona).**
Un reporte de pedidos listos para facturar, y alguien los emite. **Cuesta $0 al
año, cumple legalmente y no tiene límite de volumen.** Para un cliente que
arranca vendiendo poco, es la decisión sensata.

**3. Automatizar cuando el volumen lo justifique, no antes.** El disparador es
operativo, no técnico: **cuando transcribir a mano cueste más que el
desarrollo.** Con unos pocos pedidos al día no lo justifica; con decenas, sí.

**4. Al automatizar, preferir un proveedor que esté en el registro de la DIAN**,
para que el cliente opere amparado bajo la habilitación del proveedor en vez de
ser él el titular responsable. De los habilitados, Alegra y The Factory HKA son
los mejor documentados. **Ninguno publica el precio de su API: hay que cotizar
los dos.**

Si el cliente acepta habilitarse como software propio, se abren opciones más
baratas y con mejor sandbox. Es una decisión suya, no nuestra, y hay que
planteársela con las consecuencias claras.

**Lo que no haría:** construir el UBL y la firma nosotros, ni esperar que
aparezca una localización colombiana de ERPNext.

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

**Fase 1 — Lo que hay que hacer en cualquier caso · 4-7 días-persona**

1. Definir con el cliente el tratamiento del IVA y aplicarlo por producto
   (ojo con la plantilla de ERPNext que trae 16%).
2. Agregar tipo y número de documento al checkout.
3. Generar el `Sales Invoice` automáticamente en el momento que se acuerde.
4. Ajustar las pruebas para cubrir todo lo anterior.

**Fase 2 — Salir a facturar sin costo · 1-3 días-persona**

5. Un reporte de pedidos listos para facturar, con todo lo que pide la
   herramienta gratuita de la DIAN.
6. Acompañar al cliente en la habilitación: los siete pasos y el set de pruebas.
7. Emitir **una factura real** y verificarla de punta a punta, igual que se hizo
   con el primer pago real.

Con esto el cliente ya está facturando legalmente, a costo cero.

**Fase 3 — Automatizar, cuando el volumen lo pida · 13-20 días-persona**

8. Cotizar los proveedores habilitados y confirmar su estado en el registro.
9. Configuración y autenticación, detrás de una interfaz `emitir(factura)`.
10. Mapeo de los catálogos de la DIAN. Es la parte larga.
11. Envío al validar la factura, con estados y reintentos. Nada se le entrega al
    comprador antes de que la DIAN valide.
12. CUFE, XML, PDF con QR y entrega por correo.
13. Notas crédito para devoluciones y retracto.

**Total si se hace todo: 18-30 días-persona**, sin contar los trámites del
cliente. Pero **la fase 3 puede esperar meses**, y esa es justamente la gracia
de este orden: se sale a vender facturando bien, sin pagar un desarrollo que
todavía no se necesita.

## 9. Lo que falta verificar

Para ser honestos sobre los límites de este documento:

- **Quién firma cuando se usa un proveedor tecnológico.** Es el punto abierto
  que más pesa. La norma habla siempre de «la firma digital **del facturador
  electrónico**» y habilita contratar a un proveedor, pero no dice
  explícitamente si el proveedor puede firmar con su propio certificado en
  representación del comercio. El detalle está en la «Política de Firma» de la
  DIAN, que no se logró ubicar. **Importa para el costeo**: si el cliente
  necesita su propio certificado aunque use proveedor, es un costo y un trámite
  más. Preguntáselo al proveedor y que lo responda por escrito.
- **Bajo qué habilitación transmite cada proveedor.** Contrastalo contra el
  catálogo oficial de la DIAN el día de la decisión. En la revisión hecha, unos
  aparecían y otros no, y eso cambia quién es el titular responsable.
- **Todos los precios.** Los de la API no están publicados en ninguno de los
  proveedores habilitados. Hay que cotizar, y reconfirmar cualquier cifra el
  día de la propuesta.
- **Precios de los certificados digitales** por fuera de la vía gratuita. Las
  entidades acreditadas no publican tarifas: remiten a cotización. Circulan
  cifras por blogs que no coinciden con la vigencia oficial; no las uses.
- **El régimen tributario del cliente**, que determina toda la obligación.

Lo que **sí** quedó verificado y no hace falta volver a mirar: que ERPNext no
trae nada de Colombia, ni en el core ni en la comunidad.

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
