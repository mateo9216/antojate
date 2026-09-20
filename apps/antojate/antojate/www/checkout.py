# Copyright (c) 2026, Avantive
# For license information, please see license.txt

from antojate.api import carrito
from antojate.antojate.doctype.antojate_settings.antojate_settings import get_settings


def get_context(context):
	context.no_cache = 1
	context.body_class = "antojate"
	context.tienda = get_settings()
	context.title = "Finalizar compra"
	context.ciudades = carrito.ciudades()
	return context
