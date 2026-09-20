// Recoge los videos que dejó Playwright y arma una página para verlos.
//
// Playwright los guarda con nombres de carpeta ilegibles; acá quedan con
// nombre propio y con una portada que explica qué muestra cada uno.

import { cp, mkdir, readdir, rm, stat, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";

const ORIGEN = "resultados";
const DESTINO = "videos";

const CATALOGO = [
  {
    coincide: /recorrido-de-compra/,
    archivo: "01-recorrido-de-compra",
    titulo: "Recorrido de compra",
    resumen:
      "Del catálogo al pago: filtro por categoría, producto con presentaciones, " +
      "carrito, checkout con cálculo de envío y el cobro firmado que se le entrega a Wompi.",
  },
  {
    coincide: /como-esta-disenado/,
    archivo: "02-como-esta-disenado",
    titulo: "Cómo está diseñado",
    resumen:
      "El escritorio de ERPNext por dentro: dónde vive el producto, dónde las llaves " +
      "de pago, dónde las ciudades de envío y cómo llega cada pedido.",
  },
  {
    coincide: /defensas/,
    archivo: "03-defensas",
    titulo: "Las defensas",
    resumen:
      "Intentos reales de hacer trampa: manipular el carrito, pedir más unidades de " +
      "las que hay y espiar el pedido de otra persona. Qué responde la tienda.",
  },
  {
    coincide: /celular/,
    archivo: "04-en-el-celular",
    titulo: "En el celular",
    resumen:
      "La tienda en un teléfono, que es por donde entra la mayoría de las compras.",
  },
];

async function buscarVideos(dir) {
  const encontrados = [];
  let entradas;
  try {
    entradas = await readdir(dir, { withFileTypes: true });
  } catch {
    return encontrados;
  }
  for (const e of entradas) {
    const ruta = join(dir, e.name);
    if (e.isDirectory()) encontrados.push(...(await buscarVideos(ruta)));
    else if (e.name.endsWith(".webm")) encontrados.push(ruta);
  }
  return encontrados;
}

const videos = await buscarVideos(ORIGEN);
if (videos.length === 0) {
  console.log("No se encontraron videos. ¿Corrieron las pruebas?");
  process.exit(0);
}

await rm(DESTINO, { recursive: true, force: true });
await mkdir(DESTINO, { recursive: true });

const listos = [];
for (const ruta of videos) {
  const carpeta = dirname(ruta);
  const ficha =
    CATALOGO.find((c) => c.coincide.test(carpeta)) ?? {
      archivo: carpeta.replace(/[^a-z0-9]+/gi, "-").toLowerCase(),
      titulo: carpeta,
      resumen: "",
    };
  const destino = join(DESTINO, ficha.archivo + ".webm");
  await cp(ruta, destino);
  const { size } = await stat(destino);
  listos.push({ ...ficha, src: ficha.archivo + ".webm", mb: (size / 1048576).toFixed(1) });
  console.log(`  ${ficha.archivo}.webm  (${(size / 1048576).toFixed(1)} MB)`);
}

listos.sort((a, b) => a.archivo.localeCompare(b.archivo));

const html = `<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Antójate — recorridos grabados</title>
<style>
  :root { color-scheme: light dark; --tinta:#1f2933; --suave:#616e7c; --borde:#e4e7eb;
          --fondo:#fff; --alt:#f7f8fa; --marca:#d9480f; }
  @media (prefers-color-scheme: dark) {
    :root { --tinta:#e8eaed; --suave:#9aa5b1; --borde:#2d333b; --fondo:#12161c; --alt:#1a1f27; --marca:#ff7a45; }
  }
  * { box-sizing:border-box }
  body { margin:0; background:var(--fondo); color:var(--tinta); line-height:1.55;
         font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }
  .caja { max-width:1000px; margin:0 auto; padding:0 20px 72px }
  header { padding:56px 0 8px }
  .barra { width:58px;height:5px;background:var(--marca);border-radius:3px;margin-bottom:22px }
  h1 { font-size:clamp(28px,5vw,40px); margin:0 0 10px; letter-spacing:-.03em }
  .bajada { color:var(--suave); font-size:17px; max-width:640px; margin:0 }
  article { margin-top:48px; border:1px solid var(--borde); border-radius:14px;
            overflow:hidden; background:var(--alt) }
  video { width:100%; display:block; background:#000 }
  .pie { padding:18px 22px 22px }
  h2 { margin:0 0 6px; font-size:20px; letter-spacing:-.02em }
  .resumen { color:var(--suave); font-size:15px; margin:0 }
  .meta { color:var(--suave); font-size:13px; margin-top:10px }
  footer { margin-top:56px; color:var(--suave); font-size:14px; border-top:1px solid var(--borde); padding-top:22px }
</style>
</head>
<body>
<div class="caja">
  <header>
    <div class="barra"></div>
    <h1>Antójate — recorridos grabados</h1>
    <p class="bajada">
      No son maquetas: cada video es una prueba automatizada corriendo contra la
      tienda de verdad en un navegador real. Si algo dejara de funcionar, la
      prueba fallaría y el video no existiría.
    </p>
  </header>

${listos
  .map(
    (v) => `  <article>
    <video src="${v.src}" controls preload="metadata" playsinline></video>
    <div class="pie">
      <h2>${v.titulo}</h2>
      <p class="resumen">${v.resumen}</p>
      <div class="meta">${v.src} · ${v.mb} MB</div>
    </div>
  </article>`
  )
  .join("\n")}

  <footer>
    Generado por <code>./correr.sh</code>. Los videos se regraban en cada corrida.
  </footer>
</div>
</body>
</html>`;

await writeFile(join(DESTINO, "index.html"), html);
console.log(`\n  Abrí: ${DESTINO}/index.html`);
