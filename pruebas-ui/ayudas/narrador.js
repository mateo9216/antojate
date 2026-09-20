// Narrador de los videos.
//
// Superpone carteles sobre la página para que el video se entienda sin que
// nadie tenga que ir explicando al lado. Todo lo que dibuja es un overlay:
// no toca la página ni interfiere con lo que se está probando, porque va con
// pointer-events:none y se elimina en cada navegación.

const PAUSA_CORTA = Number(process.env.PAUSA || 1800);

/** Cartel inferior con lo que está pasando ahora. */
async function narrar(page, texto, ms = PAUSA_CORTA) {
  await page.evaluate((t) => {
    document.getElementById("__narrador")?.remove();
    const caja = document.createElement("div");
    caja.id = "__narrador";
    caja.style.cssText = [
      "position:fixed", "left:0", "right:0", "bottom:0", "z-index:2147483647",
      "background:linear-gradient(transparent,rgba(12,16,22,.94) 38%)",
      "color:#fff", "padding:46px 40px 26px", "pointer-events:none",
      "font:600 21px/1.45 ui-sans-serif,system-ui,-apple-system,sans-serif",
      "letter-spacing:-.01em", "text-shadow:0 1px 3px rgba(0,0,0,.6)",
    ].join(";");
    caja.innerHTML =
      '<div style="max-width:1000px;margin:0 auto;display:flex;gap:14px;align-items:flex-start">' +
      '<span style="flex:0 0 5px;height:26px;background:#ff7a45;border-radius:3px;margin-top:2px"></span>' +
      "<span>" + t + "</span></div>";
    document.body.appendChild(caja);
  }, texto);
  await page.waitForTimeout(ms);
}

/** Portada de capítulo: pantalla completa con el título del tramo. */
async function capitulo(page, titulo, subtitulo = "", ms = 2600) {
  await page.evaluate(
    ({ t, s }) => {
      document.getElementById("__capitulo")?.remove();
      const caja = document.createElement("div");
      caja.id = "__capitulo";
      caja.style.cssText = [
        "position:fixed", "inset:0", "z-index:2147483647",
        "background:rgba(12,16,22,.97)", "color:#fff",
        "display:flex", "flex-direction:column",
        "align-items:center", "justify-content:center",
        "pointer-events:none", "text-align:center", "padding:40px",
        "font-family:ui-sans-serif,system-ui,-apple-system,sans-serif",
        "animation:__fade .35s ease",
      ].join(";");
      caja.innerHTML =
        '<style>@keyframes __fade{from{opacity:0}to{opacity:1}}</style>' +
        '<div style="width:58px;height:5px;background:#ff7a45;border-radius:3px;margin-bottom:28px"></div>' +
        '<div style="font-size:44px;font-weight:800;letter-spacing:-.03em;max-width:900px">' + t + "</div>" +
        (s ? '<div style="font-size:21px;opacity:.72;margin-top:16px;max-width:760px;line-height:1.5">' + s + "</div>" : "");
      document.body.appendChild(caja);
    },
    { t: titulo, s: subtitulo }
  );
  await page.waitForTimeout(ms);
  await page.evaluate(() => document.getElementById("__capitulo")?.remove());
}

/** Resalta un elemento con un recuadro, para que se vea de qué se habla. */
async function señalar(page, selector, ms = 1500) {
  await page.evaluate((sel) => {
    document.getElementById("__foco")?.remove();
    const el = document.querySelector(sel);
    if (!el) return;
    const r = el.getBoundingClientRect();
    const caja = document.createElement("div");
    caja.id = "__foco";
    caja.style.cssText = [
      "position:fixed", "z-index:2147483646", "pointer-events:none",
      "border:3px solid #ff7a45", "border-radius:10px",
      "box-shadow:0 0 0 9999px rgba(12,16,22,.45)",
      `top:${r.top - 6}px`, `left:${r.left - 6}px`,
      `width:${r.width + 12}px`, `height:${r.height + 12}px`,
      "transition:all .3s ease",
    ].join(";");
    document.body.appendChild(caja);
  }, selector);
  await page.waitForTimeout(ms);
  await page.evaluate(() => document.getElementById("__foco")?.remove());
}

/** Limpia los overlays antes de una aserción que dependa de lo visible. */
async function limpiar(page) {
  await page.evaluate(() => {
    ["__narrador", "__capitulo", "__foco"].forEach((id) =>
      document.getElementById(id)?.remove()
    );
  });
}

module.exports = { narrar, capitulo, señalar, limpiar };
