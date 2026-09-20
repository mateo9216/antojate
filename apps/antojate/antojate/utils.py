# Copyright (c) 2026, Avantive
# For license information, please see license.txt

"""Ayudas disponibles dentro de las plantillas Jinja del storefront."""

from frappe.utils import flt


def pesos(valor) -> str:
	"""Formatea en pesos colombianos: $ 38.000.

	ERPNext formatea según la precisión de moneda configurada, que por defecto
	deja dos decimales. En pesos no se usan, y pelear con esa configuración
	afectaría también la contabilidad. Es más limpio formatear aquí lo que ve
	el comprador, con el mismo criterio que usa Antojate.pesos() en el JS.
	"""
	return "$ " + f"{flt(valor):,.0f}".replace(",", ".")
