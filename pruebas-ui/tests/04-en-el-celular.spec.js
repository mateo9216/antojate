// La tienda en un celular.
//
// La mayoría de las compras en Colombia entran por el teléfono, así que esto
// no es un extra: es el caso principal.

const { test, expect } = require("@playwright/test");
const { narrar, capitulo, limpiar } = require("../ayudas/narrador");

test("en el celular: la tienda se adapta", async ({ page }) => {
  await page.goto("/tienda");
  await capitulo(
    page,
    "En el celular",
    "Es por donde va a entrar la mayoría de los compradores"
  );

  await narrar(page, "El catálogo pasa a dos columnas y el buscador ocupa su propia fila.");
  await limpiar(page);
  await expect(page.locator(".tarjeta").first()).toBeVisible();

  // Que no haya scroll horizontal es la falla clásica de un diseño que no se
  // adaptó: si aparece, la tienda se siente rota en el teléfono.
  const desborde = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 1
  );
  expect(desborde, "la página no debe desbordarse a lo ancho").toBe(false);

  await page.locator(".tarjeta").first().click();
  await page.waitForLoadState("networkidle");
  await narrar(page, "La ficha del producto apila la foto sobre los datos.");
  await limpiar(page);
  await expect(page.locator("[data-agregar]")).toBeVisible();

  await page.locator("[data-agregar]").click();
  await page.getByRole("link", { name: /Carrito/ }).click();
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);
  await narrar(page, "Y el resumen del pedido queda debajo, no apretado a un lado.");
  await limpiar(page);
  await expect(page.locator(".linea")).toHaveCount(1);

  const desbordeCarrito = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 1
  );
  expect(desbordeCarrito).toBe(false);
});
