// Recorrido completo de una compra, tal como lo vive el comprador.
//
// Es una prueba de verdad: cada paso afirma algo. Y como va narrada y grabada,
// el video que sale sirve para mostrarle la tienda a alguien sin estar al lado.

const { test, expect } = require("@playwright/test");
const { narrar, capitulo, señalar, limpiar } = require("../ayudas/narrador");

test("recorrido de compra: del catálogo al pago", async ({ page }) => {
  // ---------------------------------------------------------------- catálogo
  await page.goto("/tienda");
  await capitulo(
    page,
    "Antójate",
    "Cómo compra un cliente, de principio a fin"
  );

  await narrar(
    page,
    "El catálogo. Cada producto sale de ERPNext: nombre, foto, precio y existencias reales."
  );
  const tarjetas = page.locator(".tarjeta");
  await expect(tarjetas).toHaveCount(7);

  await señalar(page, ".categorias");
  await narrar(
    page,
    "Las categorías las controla el cliente desde el escritorio, marcando una casilla."
  );

  // ------------------------------------------------------- filtro por grupo
  await page.getByRole("link", { name: "Dulces", exact: true }).click();
  await page.waitForLoadState("networkidle");
  await narrar(page, "Al filtrar por categoría solo quedan los productos de Dulces.");
  await limpiar(page);
  await expect(page.locator(".tarjeta")).toHaveCount(2);

  // -------------------------------------------------- producto con variantes
  await page.getByRole("link", { name: /Chocolate artesanal/ }).click();
  await page.waitForLoadState("networkidle");
  await narrar(
    page,
    "Este producto tiene presentaciones. Hasta que no se escoge una, no se puede comprar."
  );

  const botonAgregar = page.locator("[data-agregar]");
  await limpiar(page);
  await expect(botonAgregar).toBeDisabled();

  await señalar(page, "[data-atributo]");
  await narrar(
    page,
    "Cada sabor es un artículo distinto en ERPNext, con su propio precio y su propio stock."
  );

  await page.getByRole("button", { name: "Leche", exact: true }).click();
  await narrar(
    page,
    "Al escoger, el precio y la disponibilidad se actualizan: son los de esa presentación."
  );
  await limpiar(page);
  await expect(botonAgregar).toBeEnabled();
  await expect(page.locator("[data-mensaje-variante]")).toContainText("Disponible");

  // Agrega dos unidades.
  await page.locator("[data-mas]").click();
  await expect(page.locator("[data-cantidad]")).toHaveText("2");
  await botonAgregar.click();
  await narrar(page, "Al carrito. El contador de arriba ya lo refleja.");
  await limpiar(page);
  await expect(page.locator("[data-carrito-contador]")).toHaveText("2");

  // ------------------------------------------------- segundo producto simple
  await page.goto("/producto/CAFE-500");
  await narrar(page, "Un producto sin presentaciones se agrega directo.");
  await page.locator("[data-agregar]").click();
  await limpiar(page);
  await expect(page.locator("[data-carrito-contador]")).toHaveText("3");

  // ----------------------------------------------------------------- carrito
  await page.getByRole("link", { name: /Carrito/ }).click();
  await page.waitForLoadState("networkidle");
  await narrar(
    page,
    "El carrito vive en el navegador, pero los precios los vuelve a calcular el servidor."
  );
  await limpiar(page);
  await expect(page.locator(".linea")).toHaveCount(2);

  const subtotal = await page.locator("[data-subtotal]").textContent();
  expect(subtotal).toMatch(/\$/);

  await narrar(
    page,
    "Del navegador solo se acepta qué producto y cuántas unidades. El precio nunca viaja."
  );

  // ---------------------------------------------------------------- checkout
  await page.getByRole("link", { name: "Continuar" }).click();
  await page.waitForLoadState("networkidle");
  await narrar(page, "El checkout. No hace falta crear cuenta para comprar.");

  await page.getByLabel("Nombre completo").fill("Laura Restrepo");
  await page.getByLabel("Correo electrónico").fill("laura@ejemplo.com");
  await page.getByLabel("Celular").fill("3012223344");
  await narrar(page, "Los datos del comprador crean el cliente y el contacto en ERPNext.");

  await señalar(page, "#ciudad");
  await page.selectOption("#ciudad", "Medellín");
  await page.waitForTimeout(900);
  await narrar(
    page,
    "Al escoger la ciudad se calcula el envío. Cada ciudad tiene su costo y sus días de entrega."
  );
  await limpiar(page);
  await expect(page.locator("[data-envio]")).not.toHaveText("Escogé la ciudad");

  await page.getByLabel("Dirección").fill("Calle 10 # 43 - 25");
  await page.getByLabel(/Apartamento/).fill("Apto 502, torre B");

  // --------------------------------------------------------------- el pago
  // No vamos al Wompi real: en su lugar mostramos lo que la tienda le manda,
  // que es justamente lo que hay que verificar.
  let urlDePago = null;
  await page.route("**://checkout.wompi.co/**", async (route) => {
    urlDePago = route.request().url();
    const p = new URL(urlDePago).searchParams;
    await route.fulfill({
      contentType: "text/html; charset=utf-8",
      body: `<!doctype html><html lang="es"><body style="margin:0;font-family:ui-sans-serif,system-ui,sans-serif;background:#0c1016;color:#fff;display:grid;place-items:center;height:100vh">
        <div style="max-width:760px;padding:40px">
          <div style="width:58px;height:5px;background:#ff7a45;border-radius:3px;margin-bottom:24px"></div>
          <h1 style="font-size:34px;margin:0 0 8px;letter-spacing:-.02em">Checkout de Wompi</h1>
          <p style="opacity:.7;margin:0 0 26px;font-size:17px">
            Simulado por la prueba. Esto es lo que la tienda le entrega a Wompi:
          </p>
          <table style="width:100%;border-collapse:collapse;font-size:15px">
            ${["public-key","currency","amount-in-cents","reference","signature:integrity","redirect-url"]
              .map((k) => `<tr>
                 <td style="padding:9px 14px 9px 0;opacity:.6;white-space:nowrap;vertical-align:top">${k}</td>
                 <td style="padding:9px 0;font-family:ui-monospace,monospace;word-break:break-all">${p.get(k) || "—"}</td>
               </tr>`).join("")}
          </table>
          <p style="opacity:.55;margin-top:28px;font-size:14px;line-height:1.6">
            El monto va firmado. Si alguien lo edita en la URL, la firma deja de
            cuadrar y Wompi rechaza el cobro.
          </p>
        </div></body></html>`,
    });
  });

  await narrar(page, "Al confirmar, el servidor crea el pedido y arma el cobro firmado.");
  await page.locator("[data-pagar]").click();
  await page.waitForURL(/checkout\.wompi\.co/, { timeout: 60000 });

  // Lo que de verdad se está probando.
  expect(urlDePago).toBeTruthy();
  const params = new URL(urlDePago).searchParams;
  expect(params.get("currency")).toBe("COP");
  expect(params.get("public-key")).toMatch(/^pub_test_/);
  expect(Number(params.get("amount-in-cents"))).toBeGreaterThan(0);
  expect(params.get("reference")).toMatch(/^SAL-ORD-/);
  // La firma es un SHA256 en hexadecimal: 64 caracteres.
  expect(params.get("signature:integrity")).toMatch(/^[a-f0-9]{64}$/);

  await narrar(
    page,
    "El monto lo calculó el servidor a partir del pedido, y va firmado con SHA256.",
    2600
  );
  await narrar(
    page,
    "El pedido queda en borrador. Solo se confirma cuando Wompi avise que el pago entró.",
    2800
  );
});
