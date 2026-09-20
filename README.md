# Antójate

Tienda en línea del cliente **Antójate**, construida sobre Frappe/ERPNext v16
con cobros por **Nequi, Bancolombia, PSE y tarjeta** a través de Wompi.

## Arrancar

Solo necesitás Docker instalado.

```bash
cd deploy
./scripts/bootstrap.sh                                  # levanta todo
./scripts/bench console                                 # y luego:
>>> from antojate.demo import cargar; cargar()          # datos de ejemplo
```

Abrí **http://antojate.localhost:8080/tienda**.
Escritorio en `/desk`, con `Administrator` / `admin`.

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
│   └── 04-pruebas-de-interfaz.md       Pruebas en navegador y videos narrados
├── pruebas-ui/              Pruebas de navegador con Playwright
│   ├── tests/               Cuatro recorridos, narrados y grabados
│   ├── videos/              Los videos + index.html para verlos
│   └── correr.sh            Corre todo dentro de Docker
├── deploy/                  Todo lo necesario para correrlo
│   ├── compose.yaml         El stack
│   ├── Dockerfile           ERPNext + la app custom
│   └── scripts/             bootstrap, tunnel, migrar, recargar, pruebas
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

## Estado

Funciona de punta a punta en local, con datos de ejemplo y pruebas en verde.
Falta que el cliente se afilie a Wompi para reemplazar las llaves de prueba por
las reales. Ver `docs/02-wompi.md` para el checklist de afiliación.
