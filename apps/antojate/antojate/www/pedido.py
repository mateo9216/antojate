# Copyright (c) 2026, Avantive
# For license information, please see license.txt

import frappe

from antojate.api.pagos import _pedido_del_comprador
from antojate.antojate.doctype.antojate_settings.antojate_settings import get_settings


def get_context(context):
	context.no_cache = 1
	context.body_class = "antojate"
	context.tienda = get_settings()

	nombre = frappe.form_dict.get("name")
	token = frappe.form_dict.get("t")
	if not nombre:
		raise frappe.DoesNotExistError

	so = _pedido_del_comprador(nombre, token)

	context.pedido = so
	context.token = token
	context.title = f"Pedido {so.name}"

	# El último intento de pago manda sobre lo que se le muestra al comprador.
	ultima = frappe.get_all(
		"Wompi Transaction",
		filters={"sales_order": so.name},
		fields=["estado", "metodo_pago", "referencia"],
		order_by="creation desc",
		limit=1,
	)
	context.pago = ultima[0] if ultima else None

	if so.docstatus == 1:
		context.estado = "confirmado"
	elif context.pago and context.pago.estado in ("DECLINED", "VOIDED", "ERROR"):
		context.estado = "rechazado"
	else:
		context.estado = "esperando"

	return context
