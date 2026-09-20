# Puesta en producción

Cómo pasar de "funciona en mi máquina" a una tienda en internet vendiendo de
verdad, con plata real y productos reales.

Está escrito para hacerse de arriba abajo, una sola vez. Calculá **medio día**
de trabajo técnico, más el tiempo que el cliente se tome en afiliarse a Wompi,
que no depende de vos.

---

## 0. Antes de empezar: lo que tiene que existir

Sin estas cuatro cosas no se puede salir a producción. Conseguilas primero.

| | Quién lo consigue | Cuánto tarda |
|---|---|---|
| **Servidor** con acceso SSH | Vos, o el cliente paga | Minutos |
| **Dominio** registrado | El cliente (es suyo) | Minutos a horas |
| **Cuenta de Wompi aprobada** | El cliente | **Días**. Empezalo ya |
| **Correo saliente** (SMTP) | El cliente o ustedes | Horas |

La afiliación a Wompi es el cuello de botella real. `02-wompi.md` tiene el
checklist de documentos. Mandáselo al cliente **hoy**, aunque el servidor no
exista todavía.

---

## 1. El servidor

### Cuánto hace falta

| | Mínimo | Recomendado |
|---|---|---|
| Núcleos | 2 | 4 |
| Memoria | 4 GB | 8 GB |
| Disco | 40 GB SSD | 80 GB SSD |
| Sistema | Ubuntu 22.04 o 24.04 LTS | |

Con 2 GB de RAM no alcanza: MariaDB y los workers se quedan sin memoria y el
sitio se cae bajo cualquier carga.

Costo aproximado: **20 a 40 USD al mes** en Hetzner, DigitalOcean o Vultr.
Conviene un centro de datos en Estados Unidos (Miami o la costa este): desde
Colombia la latencia es de 40-70 ms, contra 150-200 ms desde Europa.

### Preparar el servidor

Conectate como root la primera vez y dejalo listo:

```bash
# 1. Actualizar
apt update && apt upgrade -y

# 2. Un usuario que no sea root (entrar como root a diario es mala práctica)
adduser antojate
usermod -aG sudo antojate
rsync --archive --chown=antojate:antojate ~/.ssh /home/antojate

# 3. Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker antojate

# 4. Cortafuegos: solo SSH y web
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# 5. Memoria de intercambio, por si un pico de uso se pasa de la RAM
fallocate -l 2G /swapfile && chmod 600 /swapfile
mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

Después salí y volvé a entrar como `antojate`, no como root.

**Desactivá el acceso por contraseña** en `/etc/ssh/sshd_config`
(`PasswordAuthentication no`) y entrá solo con llave SSH. Un servidor con
contraseña en el puerto 22 recibe miles de intentos de ingreso por día; no es
paranoia, es lo normal.

---

## 2. El dominio

En el panel de quien administra el DNS, creá dos registros apuntando a la IP
del servidor:

| Tipo | Nombre | Valor |
|---|---|---|
| A | `@` | La IP del servidor |
| A | `www` | La IP del servidor |

Esperá a que propague antes de seguir. Se comprueba así:

```bash
dig +short antojate.co
```

Tiene que responder la IP del servidor. Puede tardar de minutos a unas horas.

**No sigas hasta que el DNS resuelva.** Caddy pide el certificado a Let's
Encrypt validando el dominio, y si el DNS no apunta acá todavía, falla y
Let's Encrypt limita los reintentos.

---

## 3. Desplegar

```bash
git clone <URL-DEL-REPOSITORIO> antojate
cd antojate/deploy/produccion

cp .env.example .env
nano .env
```

Completá el `.env`. Las contraseñas se generan, no se inventan:

```bash
openssl rand -base64 24
```

```ini
DOMINIO=antojate.co
CORREO_TLS=tecnologia@avantive.co
DB_ROOT_PASSWORD=<generada>
ADMIN_PASSWORD=<generada>
GUNICORN_WORKERS=4          # (2 × núcleos) + 1, sin pasarte de la RAM
```

Y levantá:

```bash
./scripts/crear-sitio.sh
```

Construye la imagen, levanta todo, crea el sitio y pide el certificado. Unos
10-15 minutos. Al terminar, https://antojate.co/tienda debería responder con
la tienda vacía y el candado de HTTPS.

Si el certificado falla, casi siempre es el DNS todavía sin propagar. Mirá
`docker compose -f compose.yaml logs caddy`.

---

## 4. Configurar ERPNext

Entrá a **https://antojate.co/desk** con `Administrator` y la contraseña del
`.env`. Te recibe el asistente de configuración.

- **País:** Colombia · **Moneda:** COP · **Zona horaria:** America/Bogota
- **Nombre de la compañía:** el del cliente, como debe salir en las facturas
- **Abreviatura:** tres letras

Después del asistente, cuatro cosas que la tienda necesita para funcionar:

### 4.1 IVA

Si los productos llevan IVA, creá la plantilla de impuestos en
**Sales Taxes and Charges Template** con la tarifa que corresponda (19% en la
mayoría de los casos, 5% o exento en algunos alimentos).

**Decidí con el cliente si los precios que se publican ya incluyen IVA.** En
Colombia el comprador espera ver el precio final. Si los precios se cargan sin
IVA y el impuesto se suma en el checkout, el total va a sorprender y se pierden
ventas. Es una decisión de negocio, no técnica, pero hay que tomarla antes de
cargar el catálogo.

### 4.2 Antojate Settings

Buscá **Antojate Settings** y completá:

| Campo | Qué poner |
|---|---|
| Compañía | La que acabás de crear |
| Bodega de despacho | De donde sale el inventario real |
| Lista de precios | `Standard Selling` |
| Grupo de clientes / Territorio | Los que use el cliente |
| Cuenta contable del flete | Una cuenta de ingresos para lo cobrado por envío |
| WhatsApp | El número de atención, formato `573001234567` |

### 4.3 Ciudades de envío

**Antojate Ciudad Envio**, una por cada ciudad a la que se despacha, con su
costo, sus días y su umbral de envío gratis.

**Una ciudad que no esté acá no puede comprar.** Es la causa número uno de
"no me deja terminar el pedido".

### 4.4 Cuenta del cobro

En **Wompi Settings**, sección Contabilidad:

- **Modo de pago:** creá uno llamado `Wompi`
- **Cuenta donde entra el dinero:** una cuenta puente, no la cuenta bancaria
  final. Wompi dispersa al día siguiente, así que durante ese día el dinero
  está cobrado pero todavía no llegó al banco. Si apuntás directo a la cuenta
  bancaria, la conciliación nunca cuadra.

---

## 5. Los cobros reales

### 5.1 Cargar las llaves de producción

En **Wompi Settings**, bloque "Llaves de producción", las cuatro llaves
`*_prod_*` del panel de Wompi (Desarrolladores → Secretos para integración
técnica). Después cambiá **Ambiente** a `Producción` y guardá.

### 5.2 Registrar el webhook

En el panel de Wompi, como URL de eventos:

```
https://antojate.co/api/method/antojate.api.pagos.webhook_wompi
```

**Sin esto no funciona nada.** Los pagos entran, el dinero se cobra, y los
pedidos se quedan en borrador para siempre porque nadie avisa que se pagaron.

### 5.3 La prueba que no se puede saltar

**Hacé una compra real, con plata real, por el monto más bajo posible.**

Un sandbox en verde no garantiza que producción funcione: cambian las llaves,
cambia el dominio, cambia la ruta del webhook. Comprá algo de $1.000, pagá con
Nequi desde tu celular y verificá los cuatro eslabones:

- [ ] El pedido pasa de borrador a confirmado solo, sin que nadie lo toque
- [ ] Se creó el `Payment Entry` por el monto correcto
- [ ] El inventario bajó
- [ ] En `Wompi Transaction` figura `APPROVED` con el medio de pago usado

Si alguno falla, no salgas a producción. Y después devolvé la compra desde el
panel de Wompi.

---

## 6. El correo saliente

Sin esto, el comprador paga y no recibe ninguna confirmación. Para una tienda
nueva, sin trayectoria, eso se lee como una estafa.

En el escritorio, **Email Account** → nueva cuenta saliente, con los datos
SMTP del correo del cliente (Google Workspace, Zoho, el que usen).

No uses una cuenta de Gmail gratuita: los límites de envío son bajos y termina
marcada como spam. Si el cliente no tiene correo corporativo, un servicio de
envío transaccional (Brevo, Resend, Amazon SES) cuesta poco o nada al volumen
de una tienda que arranca.

Probalo mandándote un correo a vos mismo antes de dar por cerrado el punto.

---

## 7. Los productos reales

La guía para el cliente está en `03-guia-del-cliente.md`, escrita para que la
siga sin ayuda. Lo que conviene que sepas vos:

### Las tres condiciones

Un producto aparece en la tienda **solo si cumple las tres**:

1. Marcado **Publicar en la tienda**
2. Tiene precio en la lista configurada (`Standard Selling`)
3. Tiene existencias en la bodega configurada

Cuando el cliente diga "subí el producto y no aparece", falta una de las tres.

### Carga masiva

Para catálogos grandes, el escritorio tiene **Data Import**: se baja una
plantilla de Excel, se llena y se sube. Sirve para `Item`, `Item Price` y para
el inventario inicial vía `Stock Reconciliation`.

Hacelo en ese orden: primero los productos, después los precios, después el
inventario. Y probá con cinco filas antes de subir quinientas.

### Las fotos

Es lo que más se descuida y lo que más vende.

- Cuadradas (1:1). El catálogo las recorta a cuadrado.
- Entre 800×800 y 1200×1200. Más grande solo hace la página lenta.
- **Comprimidas antes de subir.** Una foto de 5 MB salida del celular hace que
  la tienda tarde una eternidad en el 4G del comprador. TinyPNG o Squoosh, y
  dejalas por debajo de 200 KB.
- Fondo parejo entre todas: un catálogo con fondos distintos se ve desprolijo
  aunque cada foto sea buena.

Las fotos viven en el volumen `sites`. **Entran en los respaldos solo si se
usa `--with-files`**, que es lo que hace `respaldar.sh`.

---

## 8. Respaldos

Un respaldo que nunca se restauró no es un respaldo.

```bash
cd ~/antojate/deploy/produccion
./scripts/respaldar.sh
```

Programalo todas las noches:

```bash
crontab -e
```

```cron
0 3 * * * cd /home/antojate/antojate/deploy/produccion && ./scripts/respaldar.sh >> /home/antojate/respaldos.log 2>&1
```

Tres cosas que hay que hacer y casi nadie hace:

1. **Sacar las copias del servidor.** Si se pierde el servidor, se pierden los
   respaldos que viven en él. Sincronizá `respaldos/` a S3, Backblaze o incluso
   otra máquina.
2. **Probar una restauración de verdad**, en un servidor aparte, antes de
   necesitarla. `scripts/restaurar.sh` está para eso.
3. **Respaldar antes de cada despliegue.** `desplegar.sh` ya lo hace solo.

---

## 9. Lo legal, que no es opcional

Para vender de verdad en Colombia hacen falta cosas que no son código. **Esto
no es asesoría legal**: es la lista de lo que hay que preguntarle a quien sí
lo es, antes de abrir la tienda.

- [ ] **Términos y condiciones** publicados y accesibles desde la tienda.
- [ ] **Política de tratamiento de datos personales** (Ley 1581 de 2012). Se
      están recogiendo nombre, correo, teléfono y dirección: eso son datos
      personales y hay obligaciones concretas sobre ellos.
- [ ] **Derecho de retracto** (Ley 1480, Estatuto del Consumidor): en ventas a
      distancia el comprador puede retractarse dentro de los 5 días hábiles.
      Tiene que estar informado y el negocio tiene que poder cumplirlo.
- [ ] **Política de cambios, devoluciones y garantías**, incluyendo quién paga
      el envío de una devolución.
- [ ] **Datos del comercio visibles**: razón social, NIT, dirección y teléfono.

### Facturación electrónica (DIAN)

**Esto está fuera de lo que hay construido hoy y hay que resolverlo aparte.**

ERPNext genera facturas de venta, pero **no las reporta a la DIAN**. Para
emitir factura electrónica válida en Colombia se necesita integrar un
proveedor tecnológico autorizado, o usar una localización colombiana de
ERPNext, o que el cliente facture por fuera del sistema.

Es una conversación que hay que tener con el cliente **antes** de abrir la
tienda, no después de la primera venta. Según el régimen del negocio puede ser
obligatorio desde la primera factura.

---

## 10. Checklist de salida

No abras la tienda al público hasta que todo esto esté marcado.

**Servidor**
- [ ] Contraseñas nuevas, generadas, distintas de las de desarrollo
- [ ] Acceso SSH solo por llave, sin contraseña
- [ ] Cortafuegos activo: solo 22, 80 y 443
- [ ] `developer_mode` en 0 (`crear-sitio.sh` ya lo deja así)

**Sitio**
- [ ] HTTPS con candado, y `http://` redirige a `https://`
- [ ] `host_name` configurado (lo hace `crear-sitio.sh`)
- [ ] Contraseña de `Administrator` cambiada y guardada donde corresponda
- [ ] El cliente tiene su propio usuario, no usa `Administrator`

**Cobros**
- [ ] Llaves de producción cargadas y ambiente en `Producción`
- [ ] Webhook registrado en el panel de Wompi
- [ ] **Compra real hecha y verificada de punta a punta**
- [ ] Modo de pago y cuenta contable configurados

**Operación**
- [ ] Correo saliente probado
- [ ] Respaldos programados y **una restauración probada**
- [ ] Ciudades de envío cargadas con costos reales
- [ ] Catálogo real cargado, con fotos comprimidas
- [ ] IVA definido y aplicado como se acordó

**Legal**
- [ ] Términos, política de datos y política de devoluciones publicados
- [ ] Definido cómo se va a facturar ante la DIAN

---

## 11. Operar el día a día

### Publicar una versión nueva

```bash
cd ~/antojate
git pull
cd deploy/produccion
./scripts/desplegar.sh
```

Respalda, construye, pone el sitio en mantenimiento, migra, lo saca de
mantenimiento y verifica que responda. Si algo falla, avisa y corta.

### Si un despliegue sale mal

```bash
git checkout <commit-anterior>
./scripts/desplegar.sh
```

Y si la base quedó dañada por una migración:

```bash
./scripts/restaurar.sh respaldos/<la-copia-de-antes>
```

Por eso `desplegar.sh` respalda antes de tocar nada.

### Ver qué está pasando

```bash
docker compose -f compose.yaml logs -f --tail 100 backend
docker compose -f compose.yaml ps
docker stats
```

Los errores de la aplicación quedan además en el escritorio, en **Error Log**.
Vale la pena mirarlo cada tanto: ahí aparecen los pagos que no se pudieron
conciliar, que son justo los que hay que atender a mano.

### Qué vigilar

| | Con qué frecuencia | Qué mirar |
|---|---|---|
| Error Log | Semanal | Fallos de pagos o de correo |
| Wompi Transaction | Diario los primeros días | Que no haya `APPROVED` con el pedido en borrador |
| Espacio en disco | Mensual | `df -h`. Las fotos y los respaldos crecen |
| Respaldos | Mensual | Que existan, y restaurar uno de verdad |
