# Copyright (c) 2026, Avantive
# For license information, please see license.txt

import frappe

from antojate.api import catalogo
from antojate.antojate.doctype.antojate_settings.antojate_settings import get_settings


def get_context(context):
	context.no_cache = 1
	context.body_class = "antojate"
	context.tienda = get_settings()

	grupo = frappe.form_dict.get("item_group")
	busqueda = frappe.form_dict.get("q")
	pagina = frappe.form_dict.get("pagina") or 1

	resultado = catalogo.listar_productos(item_group=grupo, busqueda=busqueda, pagina=pagina)

	context.productos = resultado["productos"]
	context.pagina = resultado["pagina"]
	context.hay_mas = resultado["hay_mas"]
	context.categorias = catalogo.categorias()
	context.grupo_activo = grupo
	context.busqueda = busqueda

	if busqueda:
		context.title = f"Buscando: {busqueda}"
	elif grupo:
		context.title = grupo
	else:
		context.title = context.tienda.nombre_tienda or "Antójate"

	return context
