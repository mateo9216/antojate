// Las defensas de la tienda, demostradas contra el sitio corriendo.
//
// No alcanza con decir "el precio lo pone el servidor": acá se intenta
// romperlo de verdad y se muestra qué pasa.

const { test, expect } = require("@playwright/test");
const { narrar, capitulo, limpiar } = require("../ayudas/narrador");

test("defensas: qué pasa si alguien intenta hacer trampa", async ({ page }) => {
  await page.goto("/tienda");
  await capitulo(
    page,
    "Las defensas",
    "Qué pasa cuando alguien intenta manipular la tienda desde su navegador"
  );

  // ------------------------------------- 1. el carrito no guarda precios
  await page.goto("/producto/CAFE-500");
  await page.locator("[data-agregar]").click();
  await page.waitForTimeout(400);

  const carrito = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("antojate:carrito") || "[]")
  );
  await narrar(
    page,
    "Esto es todo lo que el navegador guarda del carrito: qué producto y cuántas unidades."
  );
  await page.evaluate((c) => {
    const caja = document.createElement("pre");
    caja.id = "__dump";
    caja.style.cssText =
      "position:fixed;top:90px;left:50%;transform:translateX(-50%);z-index:2147483645;" +
      "background:#0c1016;color:#7ee787;padding:22px 28px;border-radius:12px;" +
      "font:15px/1.6 ui-monospace,monospace;box-shadow:0 12px 40px rgba(0,0,0,.4)";
    caja.textContent = JSON.stringify(c, null, 2);
    document.body.appendChild(caja);
  }, carrito);
  await page.waitForTimeout(2200);
  await narrar(
    page,
    "No hay ningún campo de precio que manipular. El precio lo pone el servidor, siempre.",
    2600
  );
  await page.evaluate(() => document.getElementById("__dump")?.remove());

  // La prueba de verdad: ninguna línea del carrito lleva precio.
  for (const linea of carrito) {
    expect(Object.keys(linea).sort()).toEqual(["item_code", "qty"]);
  }

  // --------------------------- 2. pedir más unidades de las que existen
  await narrar(page, "Probemos pedir 999 unidades de algo que tiene mucho menos en bodega.");
  await page.evaluate(() => {
    localStorage.setItem(
      "antojate:carrito",
      JSON.stringify([{ item_code: "CAFE-TOLIMA", qty: 999 }])
    );
  });
  await page.goto("/carrito");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1200);

  await narrar(
    page,
    "El servidor recorta la cantidad a lo que hay de verdad y lo avisa. No se puede sobrevender."
  );
  await limpiar(page);
  await expect(page.locator(".aviso.error")).toContainText(/Solo quedan/);

  // ------------------------------- 3. el pedido ajeno no se puede espiar
  await narrar(page, "Ahora, los pedidos. Creemos uno para ver cómo queda protegido.");

  const respuesta = await page.request.post(
    "/api/method/antojate.api.carrito.crear_pedido",
    {
      data: {
        items: [{ item_code: "CAFE-500", qty: 1 }],
        comprador: {
          nombre: "Prueba Playwright",
          email: "playwright@ejemplo.com",
          telefono: "3005556677",
          ciudad: "Cali",
          direccion: "Av 6 # 20-30",
        },
      },
    }
  );
  expect(respuesta.ok()).toBeTruthy();
  const { message } = await respuesta.json();

  // El token viaja dentro de la URL de regreso que se le manda a Wompi.
  const redirect = new URL(message.url_pago).searchParams.get("redirect-url");
  const token = new URL(redirect).searchParams.get("t");
  const pedido = message.pedido;
  expect(token).toMatch(/^[a-f0-9]{24}$/);

  // Con token: el comprador ve su pedido.
  await page.goto(`/pedido/${pedido}?t=${token}`);
  await narrar(
    page,
    "Con su enlace, el comprador ve su pedido sin necesidad de tener cuenta."
  );
  await limpiar(page);
  await expect(page.locator("body")).toContainText(pedido);

  // Sin token: 404. Los nombres de pedido son consecutivos y adivinables.
  await narrar(page, "Pero los números de pedido son consecutivos. ¿Y si alguien prueba el de otro?");
  const sinToken = await page.request.get(`/pedido/${pedido}`, {
    failOnStatusCode: false,
  });
  const tokenMalo = await page.request.get(`/pedido/${pedido}?t=0000000000000000000000ff`, {
    failOnStatusCode: false,
  });
  expect(sinToken.status()).toBe(404);
  expect(tokenMalo.status()).toBe(404);

  await page.goto(`/pedido/${pedido}`);
  await page.waitForLoadState("networkidle");
  await narrar(
    page,
    "Sin el token correcto, el pedido no existe. 404, aunque el número sea real.",
    2800
  );
});
