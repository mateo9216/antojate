// Recorrido por dentro: de dónde sale cada cosa que ve el comprador.
//
// Muestra el escritorio de ERPNext, que es donde el cliente administra la
// tienda, y señala las piezas que agregó la app `antojate`.

const { test, expect } = require("@playwright/test");
const { narrar, capitulo, limpiar } = require("../ayudas/narrador");

/**
 * Abre una ruta del escritorio y espera a que termine de pintar.
 *
 * El escritorio de Frappe es una aplicación de una sola página: `goto` vuelve
 * mucho antes de que el formulario exista, así que esperar la navegación no
 * alcanza. Se espera a que aparezca el contenido que se va a mostrar.
 */
async function abrirEscritorio(page, ruta, esperado) {
  // `commit`: saliendo del escritorio, que es una SPA, una navegación normal
  // se cancela a sí misma y `goto` lanza ERR_ABORTED.
  await page.goto(ruta, { waitUntil: "commit" });
  await expect(page.locator("body")).toContainText(esperado, { timeout: 60000 });
}

test("cómo está diseñado: el escritorio por dentro", async ({ page }) => {
  await page.goto("/login");
  await capitulo(
    page,
    "Cómo está diseñado",
    "La tienda es la cara pública. Por detrás vive ERPNext completo."
  );

  await narrar(page, "El cliente entra al escritorio con su usuario.");
  await page.locator("#login_email").fill("Administrator");
  await page.locator("#login_password").fill("admin");
  // El botón no trae texto en el HTML: lo escribe el JS de Frappe al cargar.
  // Por eso se busca por su clase y no por su nombre accesible.
  await page.locator("button.btn-login").click();
  // En Frappe v16 el escritorio vive en /desk; /app redirige ahí.
  // `commit` en vez del `load` por defecto: el escritorio encadena varias
  // navegaciones internas y el evento `load` no llega a estabilizarse.
  await page.waitForURL(/\/desk/, { waitUntil: "commit", timeout: 60000 });
  await expect(page.locator("body")).toContainText(/Administrator|Getting Started|Inicio/i, {
    timeout: 90000,
  });

  // ------------------------------------------------------------- el producto
  await abrirEscritorio(page, "/desk/item/CHOCO-ART", /CHOCO-ART|Chocolate artesanal/);
  await narrar(
    page,
    "Un producto es un Item de ERPNext. No inventamos un modelo nuevo: usamos el que ya existe."
  );

  await narrar(
    page,
    "La app agrega una sección 'Tienda en línea' como campos personalizados, sin tocar el core.",
    2600
  );
  await narrar(
    page,
    "Así una actualización de ERPNext no pisa nuestro trabajo, y desinstalar la app no rompe nada.",
    2800
  );

  // -------------------------------------------------------------- los cobros
  await abrirEscritorio(page, "/desk/wompi-settings", /Wompi/i);
  await narrar(
    page,
    "Las llaves de Wompi viven acá. Las privadas se guardan cifradas, nunca en el código."
  );

  await narrar(
    page,
    "Hay dos juegos de llaves: pruebas y producción. Pasar a cobrar de verdad es cambiar un campo.",
    2600
  );

  // --------------------------------------------------------------- el envío
  await abrirEscritorio(page, "/desk/antojate-ciudad-envio", /Medell|Ciudad/i);
  await narrar(
    page,
    "Las ciudades de envío, con su costo, sus días de entrega y su umbral de envío gratis."
  );
  await narrar(
    page,
    "Una ciudad que no esté en esta lista no puede comprar. El cliente la administra solo.",
    2400
  );

  // -------------------------------------------------------------- el pedido
  await abrirEscritorio(page, "/desk/sales-order", /SAL-ORD|Sales Order|Pedido/i);
  await narrar(
    page,
    "Cada compra es un Sales Order normal de ERPNext: se despacha y se factura como siempre."
  );
  await narrar(
    page,
    "Los que están en borrador son carritos que llegaron al pago y no lo completaron.",
    2400
  );

  // --------------------------------------------------------------- los pagos
  await abrirEscritorio(page, "/desk/wompi-transaction", /Wompi Transaction|APPROVED|PENDING/i);
  await narrar(
    page,
    "Cada intento de pago queda registrado: sirve para conciliar y para resolver reclamos."
  );
});
