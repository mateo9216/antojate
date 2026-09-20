# Antójate

Tienda en línea del cliente **Antójate**, construida sobre Frappe/ERPNext v16
con cobros por **Nequi, Bancolombia, PSE y tarjeta** a través de Wompi.

## Arrancar

Solo necesitás **Docker** y **git**. Nada de Python, Node, MariaDB ni Frappe
en tu máquina: todo corre en contenedores.

```bash
git clone <URL-DEL-REPOSITORIO> antojate
cd antojate/deploy
./scripts/bootstrap.sh --demo
```

Abrí **http://localhost:8080/tienda**.
Escritorio en `/desk`, con `Administrator` / `admin`.

Primera vez: entre 15 y 30 minutos, casi todo esperando la descarga de la
imagen de ERPNext. Los pasos detallados para **macOS y Windows**, con los
problemas típicos de cada uno, están en
[`docs/05-instalacion-desarrolladores.md`](docs/05-instalacion-desarrolladores.md).

Para mostrárselo al cliente desde internet, sin pagar hosting:

```bash
./scripts/tunnel.sh
```

## Qué hay acá

```
antojate/
├── docs/                    Decisiones y manuales
│   ├── 00-analisis-y-arquitectura.md   Por qué está hecho así
│   ├── 01-despliegue.md                Cómo se levanta y cómo se publica
│   ├── 02-wompi.md                     Pagos: afiliación, llaves, integración
│   ├── 03-guia-del-cliente.md          Para quien carga productos y despacha
│   ├── 04-pruebas-de-interfaz.md       Pruebas en navegador y videos narrados
│   ├── 05-instalacion-desarrolladores.md   Montarlo en macOS o Windows
│   ├── 06-produccion.md                Sacarlo a internet y vender de verdad
│   └── diagramas/                      Flujo de compra y clases (.drawio)
├── pruebas-ui/              Pruebas de navegador con Playwright
│   ├── tests/               Cuatro recorridos, narrados y grabados
│   ├── videos/              Los videos + index.html para verlos
│   └── correr.sh            Corre todo dentro de Docker
├── deploy/                  Todo lo necesario para correrlo
│   ├── compose.yaml         El stack local
│   ├── Dockerfile           ERPNext + la app custom
│   ├── scripts/             bootstrap, tunnel, migrar, recargar, pruebas
│   └── produccion/          El stack del servidor del cliente
│       ├── compose.yaml     Con Caddy y HTTPS automático
│       ├── Caddyfile
│       └── scripts/         crear-sitio, desplegar, respaldar, restaurar
└── apps/antojate/           La app de Frappe
    └── antojate/
        ├── api/             catalogo.py · carrito.py · pagos.py
        ├── antojate/doctype/  Antojate Settings · Wompi Settings ·
        │                       Wompi Transaction · Antojate Ciudad Envio
        ├── www/             tienda · producto · carrito · checkout · pedido
        ├── templates/       Base del storefront
        ├── public/          CSS, JS e imágenes
        ├── tests/           Pruebas del flujo de compra y de las firmas
        ├── demo.py          Datos de ejemplo
        └── install.py       Campos que la app agrega a ERPNext
```

## Cómo funciona, en corto

El comprador arma el carrito en su navegador. Al confirmar, el **servidor**
recalcula precios, existencias y envío, crea el `Sales Order` **en borrador** y
lo manda a pagar a Wompi con el monto firmado.

Cuando Wompi confirma el pago por webhook —y solo entonces— el pedido se
confirma, se descuenta el inventario y se registra el `Payment Entry`.

Dos reglas que no se pueden relajar:

1. **El precio nunca viene del navegador.** Del cliente solo se acepta qué
   producto y cuántas unidades.
2. **El pago solo lo confirma el webhook firmado.** El regreso del comprador a
   la página de "gracias" no prueba nada: esa URL se escribe a mano.

## Desarrollo

| Cambiaste | Corré |
|---|---|
| `.html`, `.css`, `.js` | Nada, recargá el navegador |
| `.py` | `./scripts/recargar.sh` |
| Un doctype o custom field | `./scripts/migrar.sh` |

```bash
cd deploy && ./scripts/pruebas.sh    # 16 pruebas de Python
cd pruebas-ui && ./correr.sh         # 4 recorridos en navegador real, grabados
```

Los recorridos de `pruebas-ui` dejan videos narrados en `pruebas-ui/videos/`.
Son pruebas de verdad: si la tienda se rompe, fallan y el video no se genera.
Abrí `pruebas-ui/videos/index.html` para verlos.

## Llevarlo a producción

```bash
# en el servidor, con el dominio ya apuntando a su IP
git clone <URL-DEL-REPOSITORIO> antojate
cd antojate/deploy/produccion
cp .env.example .env && nano .env
./scripts/crear-sitio.sh
```

Caddy pide el certificado de Let's Encrypt solo. El runbook completo —servidor,
DNS, IVA, llaves de Wompi, correo saliente, respaldos, lo legal y el checklist
de salida— está en [`docs/06-produccion.md`](docs/06-produccion.md).

Actualizaciones posteriores: `git pull && ./scripts/desplegar.sh`. Respalda,
migra y verifica que la tienda responda antes de darse por terminado.

## Estado

Funciona de punta a punta en local, con datos de ejemplo y todas las pruebas en
verde. Para vender de verdad faltan tres cosas que no dependen del código:

1. Que el cliente se afilie a Wompi (checklist en `docs/02-wompi.md`).
2. Un servidor y un dominio.
3. Definir cómo se factura ante la DIAN, que hoy está fuera de lo construido.
