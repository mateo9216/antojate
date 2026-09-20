# Instalación para desarrolladores

Cómo dejar Antójate corriendo en tu máquina, en macOS o en Windows.
Toma entre 15 y 30 minutos la primera vez, casi todo esperando descargas.

**No hace falta instalar Python, ni Node, ni MariaDB, ni Frappe.** Todo corre
en contenedores. Lo único que se instala en tu máquina es Docker y git.

---

## 1. Lo que necesitás

| | Versión | Para qué |
|---|---|---|
| **Docker Desktop** | Reciente | Corre todo: la aplicación, la base de datos, Redis |
| **Git** | Cualquiera | Bajar el código |
| Node.js 20+ | Opcional | Solo si vas a correr las pruebas de navegador |

**Espacio en disco: unos 8 GB.** La imagen de ERPNext pesa ~2 GB y la de
Playwright (opcional) ~3,5 GB.

**Memoria: dále al menos 4 GB a Docker.** Con menos, MariaDB y los workers
se pelean por la RAM y el sitio va a los tumbos.

---

## 2. macOS

### 2.1 Instalar Docker

Descargalo de [docker.com](https://www.docker.com/products/docker-desktop/),
eligiendo **Apple Silicon** o **Intel** según tu Mac. Si no sabés cuál tenés:
menú Apple → Acerca de este Mac. Si dice "Apple M1/M2/M3/M4", es Apple Silicon.

O con Homebrew:

```bash
brew install --cask docker
```

Abrí Docker Desktop una vez y esperá a que el ícono de la ballena deje de
moverse. **Docker Desktop tiene que estar abierto** para que los comandos
funcionen.

Subí la memoria en Ajustes → Resources → Memory: **4 GB como mínimo**, 6 si
podés.

### 2.2 Bajar el proyecto y levantarlo

```bash
git clone <URL-DEL-REPOSITORIO> antojate
cd antojate/deploy
./scripts/bootstrap.sh --demo
```

Eso es todo. `--demo` carga un catálogo de ejemplo para que no abras una
tienda vacía.

---

## 3. Windows

En Windows, Docker corre sobre **WSL2** (una máquina Linux liviana dentro de
Windows). Docker Desktop lo configura casi todo, pero hay un detalle que
importa mucho y explico más abajo.

### 3.1 Instalar WSL2

Abrí **PowerShell como administrador** y corré:

```powershell
wsl --install
```

Reiniciá el computador. Al volver, se abre una ventana de Ubuntu que pide
crear un usuario y una contraseña. Anotala: la vas a necesitar para `sudo`.

Si ya tenías WSL de antes, asegurate de que sea versión 2:

```powershell
wsl --set-default-version 2
wsl --status
```

### 3.2 Instalar Docker Desktop

Descargalo de [docker.com](https://www.docker.com/products/docker-desktop/) y
durante la instalación dejá marcado **"Use WSL 2 instead of Hyper-V"**.

Ya instalado, abrí Docker Desktop → Settings → Resources → WSL Integration y
**activá tu distribución de Ubuntu**. Sin esto, `docker` no existe dentro de
Ubuntu y nada funciona.

### 3.3 El detalle que importa: dónde clonar

**Cloná el proyecto dentro del sistema de archivos de Linux, no en `C:\`.**

Abrí la terminal de **Ubuntu** (no PowerShell, no CMD) y trabajá ahí:

```bash
cd ~
git clone <URL-DEL-REPOSITORIO> antojate
cd antojate/deploy
./scripts/bootstrap.sh --demo
```

Por qué: si clonás en `C:\Users\...` y lo usás desde Docker, cada lectura de
archivo cruza la frontera entre Windows y Linux. En un proyecto con miles de
archivos, eso vuelve todo **entre 5 y 20 veces más lento**, y los cambios en
el código a veces ni se detectan. Dentro de `~` en Ubuntu, va a velocidad
normal.

Para abrir el proyecto con VS Code desde Ubuntu:

```bash
code .
```

VS Code instala solo la extensión de WSL y edita los archivos de Linux sin
sacarlos de ahí. Es la forma recomendada.

### 3.4 Git y los finales de línea

El repositorio trae un `.gitattributes` que fuerza finales de línea LF, así
que **no hace falta configurar nada**. Si aun así ves errores raros del tipo
`bad interpreter: /usr/bin/env bash^M`, es que Git convirtió los scripts a
CRLF. Se arregla así:

```bash
git config --global core.autocrlf false
git rm --cached -r . && git reset --hard
```

---

## 4. Comprobar que quedó bien

Cuando `bootstrap.sh` termine, abrí en el navegador:

| | |
|---|---|
| Tienda | http://localhost:8080/tienda |
| Escritorio | http://localhost:8080/desk |
| Usuario | `Administrator` |
| Contraseña | `admin` |

También funciona `http://antojate.localhost:8080` en macOS y en Chrome, Edge
o Firefox de cualquier sistema. En Windows, si `antojate.localhost` no te
abre, usá `localhost` a secas: es exactamente el mismo sitio.

Deberías ver siete productos, cuatro categorías y precios en pesos. Probá
agregar algo al carrito y llegar al checkout.

Y corré las pruebas, que es la comprobación de verdad:

```bash
cd deploy && ./scripts/pruebas.sh
```

Esperá **16 pruebas en verde**.

---

## 5. El día a día

| Cambiaste | Corré |
|---|---|
| Un `.html`, `.css` o `.js` | Nada. Recargá el navegador |
| Un `.py` | `./scripts/recargar.sh` |
| Un doctype o un campo personalizado | `./scripts/migrar.sh` |

Lo de recargar tras tocar Python se olvida siempre. Los procesos cargan la
aplicación en memoria al arrancar: un `.py` editado no surte efecto hasta
reiniciarlos. Si estás persiguiendo un error que "ya arreglaste", es esto.

```bash
./scripts/bench console          # consola de Python con la app cargada
./scripts/bench migrate          # cualquier comando de bench
docker compose logs -f backend   # ver qué está pasando
docker compose down              # apagar (los datos se conservan)
docker compose down -v           # apagar y BORRAR la base de datos
```

### Pruebas de navegador (opcional)

```bash
cd pruebas-ui
npm install
./correr.sh
```

Dejan videos narrados en `pruebas-ui/videos/index.html`. Necesitan Node
instalado y descargan una imagen de Docker de ~3,5 GB la primera vez.

---

## 6. Cuando algo sale mal

| Síntoma | Qué pasa y cómo se arregla |
|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop no está abierto. Abrilo y esperá a que arranque |
| `port is already allocated` | Algo más usa el 8080. Cambiá `HTTP_PORT` en `deploy/.env` |
| La primera construcción tarda muchísimo | Normal: baja ~2 GB. Solo la primera vez |
| `502 Bad Gateway` | Reiniciaste el backend y nginx quedó apuntando a la IP vieja. Corré `./scripts/recargar.sh` |
| Cambié un `.py` y no pasa nada | `./scripts/recargar.sh` |
| El escritorio manda al asistente de configuración | Falta limpiar el caché: `./scripts/bench clear-cache` y `./scripts/recargar.sh` |
| `bad interpreter: ...^M` | Finales de línea CRLF. Mirá la sección 3.4 |
| El catálogo está vacío | Faltan los datos de ejemplo: `./scripts/datos-demo.sh` |
| Todo va lentísimo en Windows | Clonaste en `C:\`. Mové el proyecto a `~` dentro de Ubuntu (sección 3.3) |
| Quiero empezar de cero | `docker compose down -v` y después `./scripts/bootstrap.sh --demo` |

Si nada de esto aplica, los registros dicen casi siempre qué pasó:

```bash
docker compose logs --tail 100 backend
```

---

## 7. Cómo está organizado el proyecto

```
antojate/
├── apps/antojate/     La aplicación. Acá se trabaja el 90% del tiempo
│   └── antojate/
│       ├── api/       Lógica: catálogo, carrito, pagos
│       ├── www/       Las páginas públicas de la tienda
│       ├── public/    CSS, JS e imágenes
│       └── tests/     Pruebas
├── deploy/            Entorno local y scripts
│   └── produccion/    Lo que corre en el servidor del cliente
├── pruebas-ui/        Pruebas de navegador
└── docs/              Esta documentación
```

Antes de tocar código, leé `00-analisis-y-arquitectura.md`: explica por qué
las cosas están donde están, y sobre todo las dos reglas que no se relajan
(el precio nunca viene del navegador; el pago solo lo confirma el webhook).
