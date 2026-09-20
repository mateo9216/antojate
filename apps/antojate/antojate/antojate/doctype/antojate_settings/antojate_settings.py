# Copyright (c) 2026, Avantive
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AntojateSettings(Document):
	pass


def get_settings() -> "AntojateSettings":
	"""Configuración de la tienda.

	Se lee en cada página del storefront, así que va cacheada: Frappe invalida
	el caché de los Single al guardarlos, de modo que no queda desactualizada.
	"""
	return frappe.get_cached_doc("Antojate Settings")
