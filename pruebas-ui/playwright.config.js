// Configuración de las pruebas de interfaz de Antójate.
//
// Dos objetivos a la vez:
//   1. Probar de verdad la tienda en un navegador real.
//   2. Dejar el recorrido grabado en video, narrado, para mostrárselo a alguien.
//
// Por eso el video siempre se graba y las acciones van despacio: un video donde
// el cursor salta en dos frames no le explica nada a nadie.

const { defineConfig, devices } = require("@playwright/test");

// Dentro de Docker se llega por el nombre del servicio; desde el host, por
// antojate.localhost. nginx sirve el mismo sitio en ambos casos.
const BASE_URL = process.env.BASE_URL || "http://antojate.localhost:8080";

module.exports = defineConfig({
  testDir: "./tests",
  outputDir: "./resultados",

  // Las pruebas comparten la misma tienda y el mismo inventario: si corren en
  // paralelo se pisan el stock entre ellas.
  workers: 1,
  fullyParallel: false,

  timeout: 120000,
  expect: { timeout: 15000 },

  reporter: [
    ["list"],
    ["html", { outputFolder: "informe", open: "never" }],
  ],

  use: {
    baseURL: BASE_URL,
    viewport: { width: 1280, height: 800 },
    locale: "es-CO",
    timezoneId: "America/Bogota",

    video: { mode: "on", size: { width: 1280, height: 800 } },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",

    // Despacio y a propósito: esto es lo que hace el video legible.
    launchOptions: { slowMo: Number(process.env.SLOW_MO || 260) },
  },

  projects: [
    {
      name: "escritorio",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } },
      testIgnore: /celular/,
    },
    {
      name: "celular",
      use: { ...devices["Pixel 7"] },
      testMatch: /celular/,
    },
  ],
});
