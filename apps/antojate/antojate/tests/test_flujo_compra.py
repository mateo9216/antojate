# Copyright (c) 2026, Avantive
# For license information, please see license.txt

"""Flujo de compra de punta a punta.

Cubre lo que no puede fallar: que el pedido nazca en borrador, que solo el
webhook firmado lo confirme, y que un evento repetido no cobre dos veces.

Necesita los datos de demostración cargados:
    bench --site antojate.localhost console
    >>> from antojate.demo import cargar; cargar()
"""

import hashlib

import frappe
from frappe.tests import IntegrationTestCase

from antojate.api import carrito, pagos

SECRETO_EVENTOS = "test_events_pruebas"
SECRETO_INTEGRIDAD = "test_integrity_pruebas"


class TestFlujoCompra(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cfg = frappe.get_single("Wompi Settings")
		cfg.enabled = 1
		cfg.modo = "Sandbox"
		cfg.sandbox_public_key = "pub_test_pruebas"
		cfg.sandbox_private_key = "prv_test_pruebas"
		cfg.sandbox_integrity_key = SECRETO_INTEGRIDAD
		cfg.sandbox_events_key = SECRETO_EVENTOS
		# La contabilidad del cobro tiene que estar lista o el Payment Entry
		# se salta silenciosamente y la prueba no probaría nada.
		from antojate.demo import configurar_cobros

		configurar_cobros()
		cfg.reload()
		cfg.sandbox_integrity_key = SECRETO_INTEGRIDAD
		cfg.sandbox_events_key = SECRETO_EVENTOS
		cfg.sandbox_public_key = "pub_test_pruebas"
		cfg.sandbox_private_key = "prv_test_pruebas"
		cfg.enabled = 1
		cfg.save(ignore_permissions=True)
		frappe.db.commit()

		cls.item = "CAFE-500"
		cls.comprador = {
			"nombre": "Comprador de Prueba",
			"email": "prueba@ejemplo.com",
			"telefono": "3001234567",
			"ciudad": "Medellín",
			"direccion": "Calle 10 # 43-25",
		}

	def _crear_pedido(self, qty=2):
		return carrito.crear_pedido(
			items=[{"item_code": self.item, "qty": qty}],
			comprador=self.comprador,
		)

	def _evento(self, referencia, estado="APPROVED", monto_en_centavos=None):
		"""Arma un evento firmado igual que lo haría Wompi."""
		if monto_en_centavos is None:
			monto = frappe.db.get_value("Wompi Transaction", referencia, "monto")
			monto_en_centavos = int(round(monto * 100))

		transaccion = {
			"id": "wompi-" + referencia,
			"status": estado,
			"amount_in_cents": monto_en_centavos,
			"reference": referencia,
			"payment_method_type": "NEQUI",
		}
		timestamp = 1700000000
		propiedades = ["transaction.id", "transaction.status", "transaction.amount_in_cents"]
		cadena = f"{transaccion['id']}{estado}{monto_en_centavos}{timestamp}{SECRETO_EVENTOS}"

		return {
			"event": "transaction.updated",
			"data": {"transaction": transaccion},
			"timestamp": timestamp,
			"signature": {
				"properties": propiedades,
				"checksum": hashlib.sha256(cadena.encode()).hexdigest(),
			},
		}

	# -- el pedido nace en borrador -------------------------------------

	def test_el_pedido_nace_en_borrador_y_con_link_de_pago(self):
		r = self._crear_pedido()
		so = frappe.get_doc("Sales Order", r["pedido"])

		self.assertEqual(so.docstatus, 0, "el pedido no debe confirmarse antes de pagar")
		self.assertTrue(r["url_pago"].startswith("https://checkout.wompi.co/p/"))
		self.assertIn("signature%3Aintegrity", r["url_pago"])

	def test_el_precio_lo_pone_el_servidor(self):
		"""El navegador solo manda código y cantidad: el precio no viaja.

		Es la defensa contra comprar por $1: aunque el comprador manipule el
		carrito en su consola, no hay campo de precio que alterar.
		"""
		r = self._crear_pedido(qty=2)
		so = frappe.get_doc("Sales Order", r["pedido"])
		precio_real = frappe.db.get_value(
			"Item Price", {"item_code": self.item, "price_list": "Standard Selling"}, "price_list_rate"
		)
		self.assertEqual(so.items[0].rate, precio_real)

	def test_el_envio_se_agrega_segun_la_ciudad(self):
		r = self._crear_pedido(qty=1)
		so = frappe.get_doc("Sales Order", r["pedido"])
		costo = frappe.db.get_value("Antojate Ciudad Envio", "Medellín", "costo")
		gratis_desde = frappe.db.get_value("Antojate Ciudad Envio", "Medellín", "envio_gratis_desde")

		if so.net_total >= gratis_desde:
			self.assertEqual(len(so.taxes), 0, "por encima del umbral el envío es gratis")
		else:
			self.assertEqual(so.taxes[0].tax_amount, costo)

	def test_no_se_vende_a_una_ciudad_sin_cobertura(self):
		datos = dict(self.comprador, ciudad="Leticia")
		with self.assertRaises(frappe.ValidationError):
			carrito.crear_pedido(items=[{"item_code": self.item, "qty": 1}], comprador=datos)

	# -- solo el webhook confirma ---------------------------------------

	def test_el_webhook_aprobado_confirma_el_pedido(self):
		r = self._crear_pedido()
		referencia = frappe.db.get_value("Wompi Transaction", {"sales_order": r["pedido"]}, "name")

		pagos.procesar_evento(self._evento(referencia))

		so = frappe.get_doc("Sales Order", r["pedido"])
		self.assertEqual(so.docstatus, 1, "un pago aprobado debe confirmar el pedido")
		self.assertEqual(frappe.db.get_value("Wompi Transaction", referencia, "estado"), "APPROVED")

		# El ingreso tiene que quedar registrado, no solo el pedido confirmado.
		referencias_de_pago = frappe.get_all(
			"Payment Entry Reference",
			filters={"reference_name": so.name, "docstatus": 1},
		)
		self.assertEqual(len(referencias_de_pago), 1, "debe crearse exactamente un pago")

	def test_un_checksum_invalido_no_toca_el_pedido(self):
		"""Sin firma válida, el evento se descarta. Es la defensa central."""
		r = self._crear_pedido()
		referencia = frappe.db.get_value("Wompi Transaction", {"sales_order": r["pedido"]}, "name")

		evento = self._evento(referencia)
		evento["signature"]["checksum"] = "0" * 64

		resultado = pagos.procesar_evento(evento)

		self.assertIn("error", resultado)
		self.assertEqual(frappe.get_doc("Sales Order", r["pedido"]).docstatus, 0)

	def test_un_monto_distinto_no_confirma_el_pedido(self):
		"""Aunque la firma sea válida, si el monto no cuadra no se confirma."""
		r = self._crear_pedido()
		referencia = frappe.db.get_value("Wompi Transaction", {"sales_order": r["pedido"]}, "name")

		# Firma correcta, pero pagando 100 pesos por todo el pedido.
		pagos.procesar_evento(self._evento(referencia, monto_en_centavos=10000))

		self.assertEqual(frappe.get_doc("Sales Order", r["pedido"]).docstatus, 0)

	def test_el_evento_repetido_no_se_aplica_dos_veces(self):
		"""Wompi reintenta hasta 3 veces; procesar dos veces sería cobrar doble."""
		r = self._crear_pedido()
		referencia = frappe.db.get_value("Wompi Transaction", {"sales_order": r["pedido"]}, "name")
		evento = self._evento(referencia)

		pagos.procesar_evento(evento)
		pagos.procesar_evento(evento)

		pagos_creados = frappe.get_all(
			"Payment Entry Reference",
			filters={"reference_name": r["pedido"], "docstatus": 1},
		)
		self.assertEqual(len(pagos_creados), 1, "no puede haber dos pagos para el mismo pedido")
		self.assertEqual(frappe.get_doc("Sales Order", r["pedido"]).docstatus, 1)

	def test_un_pago_rechazado_no_confirma_el_pedido(self):
		r = self._crear_pedido()
		referencia = frappe.db.get_value("Wompi Transaction", {"sales_order": r["pedido"]}, "name")

		pagos.procesar_evento(self._evento(referencia, estado="DECLINED"))

		self.assertEqual(frappe.get_doc("Sales Order", r["pedido"]).docstatus, 0)
		self.assertEqual(frappe.db.get_value("Wompi Transaction", referencia, "estado"), "DECLINED")
