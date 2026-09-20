# Despliegue

## Fase 1 — Levantarlo en tu máquina

Lo único que necesitás instalado es Docker.

```bash
cd antojate/deploy
./scripts/bootstrap.sh
```

Tarda unos minutos la primera vez (descarga la imagen de ERPNext, ~2 GB).
Cuando termine:

| | |
|---|---|
| Tienda | http://antojate.localhost:8080/tienda |
| Escritorio | http://antojate.localhost:8080/desk |
| Usuario | `Administrator` |
| Contraseña | `admin` |

`.localhost` resuelve solo en el navegador: no hay que tocar `/etc/hosts`.

### Cargar datos de demostración

El sitio nace vacío. Para verlo con catálogo, categorías, variantes,
existencias y ciudades de envío:

```bash
./scripts/bench console
>>> from antojate.demo import cargar; cargar()
```

Crea la compañía, siete productos (dos con variantes), seis ciudades y deja la
tienda configurada. Es idempotente: se puede correr de nuevo sin duplicar nada.

### El ciclo de trabajo diario

| Qué cambiaste | Qué correr |
|---|---|
| Un `.html`, `.css` o `.js` | Nada. Recargá el navegador |
| Un `.py` | `./scripts/recargar.sh` |
| Un doctype o un custom field | `./scripts/migrar.sh` |
| Querés correr las pruebas | `./scripts/pruebas.sh` |

Lo de recargar tras tocar Python no es capricho: los procesos cargan la app en
memoria al arrancar, así que un `.py` editado no se aplica hasta reiniciarlos.
Perder tiempo buscando un bug que ya estaba arreglado es el error clásico aquí.

### Comandos útiles

```bash
./scripts/bench migrate          # cualquier comando de bench contra el sitio
./scripts/bench console          # consola de Python con la app cargada
docker compose logs -f backend   # ver qué está pasando
docker compose down              # apagar (los datos se conservan)
docker compose down -v           # apagar y BORRAR la base de datos
```

## Fase 2 — Que el cliente lo vea, sin pagar hosting

```bash
./scripts/tunnel.sh
```

Levanta un túnel de Cloudflare y te imprime una URL `https://…trycloudflare.com`
que podés pasarle al cliente. No pide cuenta, ni dominio, ni tarjeta.

Tres cosas que conviene tener claras antes de mandarla:

1. **Vive mientras tu máquina esté encendida** y el contenedor arriba. Si
   apagás el computador, la URL muere. Acordá una hora con el cliente.
2. **La URL cambia cada vez** que reiniciás el túnel. No sirve para imprimir en
   una tarjeta; sirve para mostrar avances.
3. **Es pública.** Cualquiera con el enlace entra, y eso incluye `/desk`. Antes
   de mandarla, cambiá la contraseña de `Administrator`, que por defecto es la
   de desarrollo:

   ```bash
   ./scripts/bench set-admin-password '<una contraseña buena>'
   ```

   Tampoco es para datos reales de clientes reales todavía.

Esa misma URL es la que hay que cargar en Wompi como destino del webhook
mientras estemos en sandbox (ver `02-wompi.md`).

Para bajarlo:

```bash
docker compose --profile tunnel down cloudflared
```

## Fase 3 — Producción, cuando haya presupuesto

La arquitectura no cambia. Lo que cambia es dónde corre y qué se endurece.

### Dónde

| Opción | Costo aprox. | Cuándo conviene |
|---|---|---|
| VPS propio (Hetzner, DigitalOcean) | 20-40 USD/mes | Por defecto. El mismo `docker compose` de aquí |
| El GKE que ya operan | Marginal | Si prefieren un solo lugar que administrar |
| Frappe Cloud | 25-50 USD/mes por sitio | Si no quieren administrar servidores |

### Qué hay que cambiar antes de abrir al público

- [ ] Contraseñas nuevas: `DB_ROOT_PASSWORD` y la de `Administrator`. Las de
      este repo son para desarrollo local y son públicas.
- [ ] Dominio propio apuntando al servidor, con TLS (Traefik o Caddy delante).
- [ ] `developer_mode` en 0.
- [ ] Backups automáticos de la base y de la carpeta `sites` (ahí viven las
      imágenes de los productos), con una restauración probada de verdad.
- [ ] Llaves de producción de Wompi y el webhook apuntando al dominio real.
- [ ] Correo saliente configurado, o el comprador nunca recibe su confirmación.

### Mudanza de los datos

Lo que hoy tenés local se lleva tal cual:

```bash
# en tu máquina
./scripts/bench backup --with-files

# copiás el backup al servidor y allá
bench --site antojate.co restore <archivo.sql.gz> \
  --with-public-files <archivo-files.tar>
```
