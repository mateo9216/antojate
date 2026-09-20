# Copyright (c) 2026, Avantive
# For license information, please see license.txt

"""Instalación de la app.

Todo lo que necesitamos de ERPNext lo agregamos como Custom Field. No se
modifica ningún doctype del core: así una actualización de ERPNext no pisa
nuestro trabajo, y desinstalar la app no deja el sistema roto.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CAMPOS_TIENDA = {
	"Item": [
		{
			"fieldname": "antojate_sec",
			"fieldtype": "Section Break",
			"label": "Tienda en línea",
			"insert_after": "description",
			"collapsible": 1,
		},
		{
			"fieldname": "antojate_publicado",
			"fieldtype": "Check",
			"label": "Publicar en la tienda",
			"insert_after": "antojate_sec",
			"description": "Si no está marcado, el producto no aparece en el sitio público.",
		},
		{
			"fieldname": "antojate_destacado",
			"fieldtype": "Check",
			"label": "Destacado en la portada",
			"insert_after": "antojate_publicado",
			"depends_on": "eval:doc.antojate_publicado",
		},
		{
			"fieldname": "antojate_orden",
			"fieldtype": "Int",
			"label": "Orden de aparición",
			"insert_after": "antojate_destacado",
			"default": "999",
			"description": "Menor número aparece primero. Déjalo en 999 si no te importa el orden.",
		},
		{
			"fieldname": "antojate_col",
			"fieldtype": "Column Break",
			"insert_after": "antojate_orden",
		},
		{
			"fieldname": "antojate_descripcion_larga",
			"fieldtype": "Text Editor",
			"label": "Descripción para la tienda",
			"insert_after": "antojate_col",
			"description": "Lo que lee el comprador en la ficha del producto.",
		},
	],
	"Sales Order": [
		{
			"fieldname": "antojate_telefono",
			"fieldtype": "Data",
			"label": "Celular del comprador",
			"insert_after": "contact_email",
			"read_only": 1,
			"description": (
				"No se usa po_no para esto: ERPNext exige que po_no sea único por "
				"cliente, así que un comprador que volviera no podría hacer un "
				"segundo pedido."
			),
		},
		{
			"fieldname": "antojate_token",
			"fieldtype": "Data",
			"label": "Token de la tienda",
			"insert_after": "antojate_telefono",
			"read_only": 1,
			"hidden": 1,
			"no_copy": 1,
			"print_hide": 1,
			"description": (
				"Secreto que permite al comprador ver su pedido sin iniciar sesión. "
				"Los nombres de pedido son consecutivos y adivinables; el token no."
			),
		},
	],
	"Item Group": [
		{
			"fieldname": "antojate_publicado",
			"fieldtype": "Check",
			"label": "Mostrar como categoría en la tienda",
			"insert_after": "item_group_name",
		},
		{
			"fieldname": "antojate_orden",
			"fieldtype": "Int",
			"label": "Orden de la categoría",
			"insert_after": "antojate_publicado",
			"default": "999",
		},
	],
}


def after_install():
	create_custom_fields(CAMPOS_TIENDA, ignore_validate=True)
	frappe.db.commit()
