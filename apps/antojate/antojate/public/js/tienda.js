/* Antójate — carrito del comprador.
 *
 * El carrito vive en el navegador (localStorage) y solo guarda qué producto y
 * cuántas unidades. Ni precios ni totales: esos los recalcula el servidor en
 * cada paso. Si aquí se guardara el precio, cualquiera lo editaría desde la
 * consola y compraría por lo que quisiera.
 */
(function () {
  "use strict";

  var CLAVE = "antojate:carrito";

  var Carrito = {
    leer: function () {
      try {
        var datos = JSON.parse(localStorage.getItem(CLAVE) || "[]");
        return Array.isArray(datos) ? datos : [];
      } catch (e) {
        // localStorage bloqueado o contenido corrupto: se empieza de cero en
        // vez de romper toda la página.
        return [];
      }
    },

    guardar: function (items) {
      try {
        localStorage.setItem(CLAVE, JSON.stringify(items));
      } catch (e) {
        /* modo privado sin cuota: el carrito dura lo que la pestaña */
      }
      Carrito.pintarContador();
      document.dispatchEvent(new CustomEvent("carrito:cambio", { detail: items }));
    },

    agregar: function (itemCode, qty) {
      var items = Carrito.leer();
      var existente = items.filter(function (i) { return i.item_code === itemCode; })[0];
      if (existente) {
        existente.qty += qty || 1;
      } else {
        items.push({ item_code: itemCode, qty: qty || 1 });
      }
      Carrito.guardar(items);
    },

    cambiar: function (itemCode, qty) {
      var items = Carrito.leer().map(function (i) {
        if (i.item_code === itemCode) { i.qty = qty; }
        return i;
      }).filter(function (i) { return i.qty > 0; });
      Carrito.guardar(items);
    },

    quitar: function (itemCode) {
      Carrito.guardar(Carrito.leer().filter(function (i) { return i.item_code !== itemCode; }));
    },

    limpiar: function () { Carrito.guardar([]); },

    unidades: function () {
      return Carrito.leer().reduce(function (t, i) { return t + (i.qty || 0); }, 0);
    },

    pintarContador: function () {
      var n = Carrito.unidades();
      Array.prototype.forEach.call(document.querySelectorAll("[data-carrito-contador]"), function (el) {
        el.textContent = n;
        el.style.display = n > 0 ? "" : "none";
      });
    }
  };

  function pesos(valor) {
    return new Intl.NumberFormat("es-CO", {
      style: "currency", currency: "COP", maximumFractionDigits: 0
    }).format(valor || 0);
  }

  /* Llama a un método whitelisted de la app. Frappe expone /api/method/... */
  function llamar(metodo, args) {
    return fetch("/api/method/" + metodo, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Frappe-CSRF-Token": (window.frappe && window.frappe.csrf_token) || ""
      },
      body: JSON.stringify(args || {})
    }).then(function (r) {
      return r.json().then(function (cuerpo) {
        if (!r.ok) {
          var msg = "No pudimos completar la operación.";
          try {
            // Frappe devuelve el mensaje de frappe.throw dentro de _server_messages.
            var m = JSON.parse(cuerpo._server_messages || "[]");
            if (m.length) { msg = JSON.parse(m[0]).message; }
          } catch (e) { /* se queda el mensaje genérico */ }
          throw new Error(msg);
        }
        return cuerpo.message;
      });
    });
  }

  window.Antojate = { Carrito: Carrito, pesos: pesos, llamar: llamar };

  document.addEventListener("DOMContentLoaded", Carrito.pintarContador);
})();
