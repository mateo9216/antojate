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

### 2.3 Pedir la identificación del comprador — y solo lo justo

El checkout pide nombre, correo, celular, ciudad y dirección. **No pide
documento de identidad**, y la factura lo necesita.

Pero acá la norma no solo obliga: **también limita**. Si el comprador quiere la
factura a su nombre, **solo se le pueden pedir tres datos**: nombre o razón
social, tipo y número de identificación, y correo electrónico. Pedir más es una
infracción. Y si no pide factura a su nombre, **no se le pueden pedir esos datos
en absoluto**.

Eso define el diseño, y de paso resuelve la preocupación de que pedir la cédula
espante ventas:

```
  [ ] ¿Necesitás la factura a tu nombre?

   Sin marcar  →  se factura a "consumidor final", con el NIT 222222222222.
                  No se pide ningún dato extra.
   Marcado     →  aparecen exactamente tres campos: nombre, tipo y número de
                  documento, y correo.
```

Un detalle que conviene tener presente: **cuando se factura a consumidor final
o sin NIT, la dirección de entrega es obligatoria en el XML**. Eso el checkout
ya lo captura, así que no hay trabajo nuevo ahí.

### 2.4 Y hay que facturar en el momento de la venta

La DIAN lo ha dicho expresamente para comercio electrónico: la factura se
expide **cuando se perfecciona la venta**, es decir cuando comprador y vendedor
acuerdan bien y precio por el canal digital. **No hay plazo de gracia** y la
entrega física del producto no es lo que dispara la obligación.

Para la arquitectura esto significa una cosa concreta: **el disparador es el
webhook de pago de Wompi**, no un proceso nocturno. Y tiene una consecuencia
incómoda para la ruta manual, que está dicha más abajo.

## 3. Qué exige la norma

Verificado contra el micrositio oficial de la DIAN (septiembre de 2026).

### Quién está obligado

> «Las personas o empresas que venden bienes o prestan servicios deberán
> expedir factura», «a excepción de las que por expresa disposición legal no
> están obligadas a expedir factura».

El fundamento es el **artículo 615 del Estatuto Tributario** y el **artículo
1.6.1.4.1 del Decreto Único Reglamentario 1625 de 2016**.

La norma nombra expresamente, entre los obligados, a «los comerciantes,
importadores o prestadores de servicios o **en las ventas a consumidores
finales**». Una tienda en línea que vende productos físicos es comerciante:
**está obligada, y no hay un régimen de "comercio pequeño" que la exima por ser
pequeña**.

**La única salida real** es que el dueño sea **persona natural no responsable de
IVA**, y exige cumplir **todas** estas condiciones a la vez: ingresos brutos por
debajo de 3.500 UVT (unos $183 millones en 2026), un solo establecimiento, sin
franquicia ni concesión, no ser usuario aduanero, sin contratos individuales que
superen ese tope, y **consignaciones o inversiones financieras por debajo de
3.500 UVT**.

Esa última condición es la que rompe el esquema en un e-commerce: **todo lo que
cobra Wompi entra por cuenta bancaria**. Basta con vender bien un año para
caerse de la exención y quedar obligado.

Y ojo con algo: si quien no está obligado **decide** facturar igual, la norma
lo considera obligado para efectos tributarios y le exige cumplir todos los
requisitos. No hay término medio.

**Conclusión práctica:** salvo que el dueño sea persona natural con facturación
muy baja y quiera quedarse ahí, hay que planear como obligado desde el día uno.
Si constituye una SAS, está obligado sin discusión.

### Qué documento se emite

El sistema de facturación electrónica abarca la factura electrónica de venta,
los documentos equivalentes electrónicos, las notas crédito y débito, el
documento soporte y el RADIAN.

Para esta tienda hay dos que importan:

- **Factura electrónica de venta.** Es la que corresponde a una venta a
  distancia con datos del comprador.
- **Nota crédito electrónica.** Es el mecanismo para anular o devolver, y hay
  que construirla desde el principio, por cuatro motivos:
  1. **Derecho de retracto** (Ley 1480, art. 47, **reformado por la Ley 2439
     de 2024**): el comprador tiene 5 días hábiles desde la entrega, y hay que
     devolverle **todo** lo pagado, sin descuentos ni retenciones.

     Tres cosas de esa reforma cambian el diseño, no solo la política:

     - **El plazo para devolver el dinero en comercio electrónico es de 15 días
       calendario**, no los 30 de la redacción anterior. Ojo con esto: varias
       fuentes en internet todavía publican el artículo sin la reforma.
     - **El reloj no arranca con la solicitud.** Arranca cuando se cumplen dos
       condiciones: que el comprador haya dado los datos completos **y** haya
       devuelto el producto. Son dos compuertas en el flujo, no una fecha.
     - **El reembolso va sobre el mismo medio de pago** con el que se pagó,
       salvo acuerdo distinto. Con Wompi eso significa **usar su mecanismo de
       reembolso sobre la transacción original**, no hacer una transferencia
       por fuera. Y hay que informarle al comprador, de forma clara, qué
       opciones de devolución tiene.

     Hay excepciones al retracto —perecederos, bienes de uso personal, productos
     personalizados— que pueden cubrir buena parte de un catálogo de alimentos,
     **pero eso se valida producto por producto con el abogado del cliente, no
     se asume**.
  2. **Reversión del pago** (Ley 1480, art. 51): aplica directamente porque se
     cobra con PSE y tarjeta. El comprador tiene **5 días hábiles** para
     reclamar, y quienes participan del pago tienen **15 días hábiles** para
     hacer efectiva la reversión.
  3. Devoluciones de mercancía.
  4. **El set de pruebas de habilitación la exige**, junto con la nota débito.
     O sea: hay que implementar ambas aunque la nota débito casi no se use en
     una tienda que cobra por anticipado.

  Una regla que condiciona el diseño: la nota crédito es el mecanismo de
  anulación, y **el número de la factura anulada no se puede reutilizar**.

  Para cuando toque programarlo, los conceptos que admite la nota crédito son
  seis: devolución parcial, **anulación de la factura**, rebaja o descuento,
  ajuste de precio, descuento por pronto pago y descuento por volumen. No hay
  un concepto "otros". Además hay dos tipos: **con referencia a la factura o
  sin ella**, y **la anulación exige el que lleva referencia**, apuntando al
  CUFE original.

  El mapeo para esta tienda: una devolución parcial es el concepto de devolución
  parcial; **un retracto es una anulación**, porque deshace el contrato entero.
  Ojo: esa equivalencia es de contenido económico, la norma tributaria no
  menciona el retracto. Confirmá los códigos exactos contra el anexo del
  proveedor que se contrate.

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

Tres precisiones sobre ese set, porque circulan mal:

- **No hay límite de intentos ni plazo máximo.** Se reintenta hasta pasar.
- **La DIAN no publica un número fijo de documentos** para software propio: de
  hecho tres páginas oficiales suyas se contradicen. El número que manda es el
  que muestra el portal en el detalle del set. **No le prometas una cifra al
  cliente.**
- **Se exige igual si se usa un proveedor.** La diferencia es que el proveedor
  lo corre por vos, y suele ser cuestión de horas.

Y sobre cuánto tarda todo el trámite: **la DIAN no publica ningún plazo**. Las
cifras que circulan —"tres meses de pruebas", "cinco días hábiles para aprobar"—
**no existen en la norma**. El cuello de botella real es conseguir el
certificado y que el software genere documentos correctos, no la respuesta de
la DIAN, que es automática. No le des al cliente un número más preciso que eso.

---

### Qué pasa si no se factura

Conviene tenerlo claro, porque es lo que hace que la conversación con el
cliente deje de postergarse.

Son **tres conductas distintas**, con tres sanciones distintas:

| Conducta | Sanción | Tope |
|---|---|---|
| **No expedir** la factura | Cierre de 3 días | Sustituible por multa del **5% de los ingresos operacionales del mes anterior** |
| **Expedirla sin los requisitos** | 1% de lo facturado | 950 UVT (~$49,7 millones en 2026) |
| **No transmitirla, o transmitirla mal** | 1% de lo no informado (0,7% si es errónea, 0,5% si es extemporánea) | **7.500 UVT (~$392,8 millones)** |

Sobre la multa sustitutiva del cierre: aplica **sin importar que no haya local
físico**, y la base son los ingresos **del contribuyente**, no solo los del
punto sancionado.

**La tercera fila es la que nos toca a nosotros.** Una tienda que genere la
factura pero falle al transmitirla —webhook caído, reintentos mal hechos, una
cola sin lugar donde caigan los fallos— cae ahí. **Es riesgo puro de
ingeniería, y su tope es ocho veces el de facturar mal.**

De ahí sale un requisito, no una recomendación: **el sistema necesita
reintentos, monitoreo y una alerta sobre documentos generados que no llegaron a
quedar validados.** Un documento emitido y no transmitido no puede quedar en
silencio esperando a que alguien lo note.

### Qué campo roto cuesta multa y cuál cuesta cierre

Los requisitos de la factura se parten en dos grupos, y la diferencia importa:

- **Cierre directo, sin multa previa:** NIT del vendedor, NIT del adquirente con
  el IVA discriminado, **numeración consecutiva**, **fecha de expedición**,
  **descripción de los artículos** y **valor total**.
- **Multa primero, cierre solo por reincidencia:** la denominación «factura de
  venta», los datos del impresor y la calidad de retenedor de IVA.

Leelo de nuevo mirando la primera lista: **son exactamente los campos que más
fácil se rompen en una integración automática.** Un consecutivo que se salta,
una fecha con la zona horaria equivocada, un total que no cuadra por redondeo.
Ahí es donde van las validaciones más duras, no en los campos cosméticos.

Una noticia buena, por contraste: la DIAN ha conceptuado que **los errores en la
identificación del comprador no son conducta sancionable**, siempre que la
factura cumpla los demás requisitos. Si alguien teclea mal su cédula en el
checkout, se corrige anulando con nota crédito y expidiendo de nuevo. Eso le
quita presión al diseño de ese campo.

**Pero el riesgo caro es otro.** Sin factura con los requisitos, **no proceden
costos ni deducciones en renta, ni IVA descontable**. Traducido: el peligro real
no es que le cierren la tienda al cliente, es que en una fiscalización le
rechacen los costos y termine pagando renta sobre el ingreso bruto. Eso suele
ser un orden de magnitud peor que la sanción formal.

Lo mismo aplica al revés, y por eso vale nombrarlo: cuando la tienda **le
compre** a alguien que no está obligado a facturar —un proveedor pequeño, un
domiciliario independiente— hace falta el **documento soporte en adquisiciones
a no obligados**, o esa compra no es deducible.

Ese documento es bastante menos exigente que la factura de venta: tiene su
propio código (el **CUDS**) y se puede emitir en el momento de cada operación
**o acumular la semana con un mismo proveedor**, transmitiendo a más tardar el
último día hábil. Solo existe acumulación semanal, no quincenal ni mensual. En
código: un trabajo semanal, no algo en tiempo real.

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

**El problema, y es más fuerte de lo que parece.** No es solo que no tenga API:
sus propios términos y condiciones **prohíben conectarle software**. Textual:
«el usuario **no podrá subir o cargar archivos planos ni establecer conexión
desde la solución gratuita con ninguna aplicación de software**». Las
"plantillas" que anuncia son captura rápida dentro del portal, no una carga
masiva. Alguien tiene que pasar cada pedido a mano, y punto.

Dos limitaciones más, del mismo documento: **no almacena los documentos**
—se descargan al generarlos y la conservación queda por cuenta del usuario— y
**la cuenta se inactiva si no se ingresa en seis meses**.

- **Desarrollo:** ninguno. Con un reporte de pedidos listos para facturar,
  1-3 días-persona.
- **Costo:** **$0 al año**, certificado incluido.

**Lo que se pierde, dicho sin adornos** —porque esta es la ruta que recomiendo
para arrancar, y conviene entrar con los ojos abiertos:

- **El CUFE, el XML y el PDF no vuelven a ERPNext.** La tienda nunca sabe si una
  venta quedó facturada: hay que confiar en que alguien lo hizo. Se rompe la
  cadena pedido ↔ pago ↔ factura, que es justamente la que hoy sí está entera.
- **La numeración queda partida entre dos sistemas**, con el riesgo de saltos o
  duplicados contra la resolución autorizada.
- **Las devoluciones y notas crédito viven solo en la otra herramienta.**
- **El comprador no recibe su factura al pagar**, sino cuando alguien la emita.

**Y una tensión que hay que poner sobre la mesa:** la DIAN ha dicho para
comercio electrónico que la factura se expide **cuando se perfecciona la venta,
sin plazo de gracia**. Transcribir a mano introduce una demora. Que una emisión
manual el mismo día sea aceptable es **exactamente el tipo de pregunta para el
contador del cliente**, y hay que hacérsela antes de adoptar esta ruta, no
después.

Nada de esto impide arrancar así. Pero define el disparador para automatizar:
**cuando ese desorden empiece a costar más que el desarrollo.**

**Un dato que mejora mucho esta ruta:** los modos de operación **no son
excluyentes**. Se puede estar habilitado en la solución gratuita **y** en otro
modo a la vez, usando **prefijos de numeración distintos**. O sea que arrancar
acá no cierra ninguna puerta, y después la gratuita queda como plan de
contingencia manual si el proveedor se cae.

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

- **Cuidado con el precio de Alegra.** Publica planes desde ~$17.900/mes con
  facturas ilimitadas y certificado incluido, pero esos son los de su
  **aplicación**. Para integrar desde un sistema propio tienen además un
  producto para casas de software cuyo precio **no está publicado**. Al cotizar,
  **preguntá explícitamente cuál de los dos aplica**: es un error fácil de
  cometer y cambia el costo del proyecto.
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

**Y hay que hablarle a la DIAN en SOAP.** No expone API REST: todo va por
servicios web SOAP con WS-Security. Sumale armar el UBL 2.1, calcular el CUFE
con SHA-384, firmar en XAdES-EPES con un certificado de entidad acreditada, y
manejar los rangos de numeración y las contingencias.

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

  Hay un indicio útil: al menos uno de los proveedores habilitados permite
  elegir entre firmar con **su** certificado o con el **del comercio**, lo que
  sugiere que ambos esquemas son admisibles. Es un indicio, no una confirmación:
  sigue haciendo falta la respuesta por escrito.
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
