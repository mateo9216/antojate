# Diagramas

Dos archivos `.drawio`, editables. No son imágenes: se abren, se modifican y
se vuelven a guardar.

| Archivo | Qué explica |
|---|---|
| `flujo-de-compra.drawio` | El recorrido completo: del catálogo al pedido confirmado, con todos los caminos alternos y las tres validaciones del webhook |
| `clases.drawio` | El modelo: qué escribimos nosotros, qué doctypes propios hay y qué se reusa de ERPNext |

## Cómo abrirlos

**Sin instalar nada:** entrá a [app.diagrams.net](https://app.diagrams.net),
elegí *Open Existing Diagram* y cargá el archivo.

**En VS Code:** instalá la extensión *Draw.io Integration*
(`hediet.vscode-drawio`) y hacé doble clic en el archivo. Queda editable al
lado del código, y los cambios se versionan como cualquier otro archivo.

**De escritorio:** [drawio-desktop](https://github.com/jgraph/drawio-desktop/releases).

## Las imágenes

En `export/` hay un PNG de cada diagrama, para pegar en presentaciones o
mandárselos a alguien que no va a abrir draw.io. **Son derivados**: si tocás el
`.drawio`, regeneralos con

```bash
cd docs/diagramas
docker run --rm -v "$PWD":/data rlespinasse/drawio-export:latest \
  -f png --scale 1.5 --remove-page-suffix .
```

## Al modificarlos

Son documentación, así que se desactualizan si nadie los mantiene. Dos casos
en los que hay que tocarlos:

- **Cambió el flujo de compra o de pago** → `flujo-de-compra.drawio`.
- **Se agregó un doctype o un campo importante** → `clases.drawio`.

Guardalos siempre en formato `.drawio` (o *Editable XML*), no como PNG: un PNG
no se puede volver a editar y el siguiente que lo necesite va a tener que
dibujarlo de nuevo.

## Cómo leerlos

Los colores significan lo mismo en los dos:

| Color | Qué es |
|---|---|
| Verde | Lo que escribimos nosotros |
| Azul | Nuestros doctypes, o el comprador en el flujo |
| Morado | ERPNext, que se reusa sin tocarlo |
| Naranja | Wompi |
| Rojo | Caminos alternos y errores |

En el diagrama de clases, un `+` delante de un campo quiere decir que es un
campo que **nuestra app le agrega** a un doctype de ERPNext, sin modificar el
original.
