# Copyright (c) 2026, Avantive
# For license information, please see license.txt

import json

import frappe

from antojate.api import catalogo
from antojate.antojate.doctype.antojate_settings.antojate_settings import get_settings


def get_context(context):
	context.no_cache = 1
	context.body_class = "antojate"
	context.tienda = get_settings()

	item_code = frappe.form_dict.get("item_code")
	producto = catalogo.obtener_producto(item_code) if item_code else None

	if not producto:
		# 404 de verdad: así el navegador y los buscadores no indexan una ficha
		# de un producto que ya no se vende.
		raise frappe.DoesNotExistError

	context.producto = producto
	context.title = producto["item_name"]
	# Las variantes se serializan para que el selector las resuelva sin ir al
	# servidor en cada clic.
	context.variantes_json = json.dumps(producto["variantes"], ensure_ascii=False)
	return context
