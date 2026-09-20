# Copyright (c) 2026, Avantive
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

URL_API = {
	"Sandbox": "https://sandbox.wompi.co/v1",
	"Producción": "https://production.wompi.co/v1",
}

URL_CHECKOUT = "https://checkout.wompi.co/p/"


class WompiSettings(Document):
	def validate(self):
		if not self.enabled:
			return
		faltantes = [etiqueta for etiqueta, valor in self._llaves_del_modo().items() if not valor]
		if faltantes:
			frappe.throw(
				_("Faltan estas llaves para el ambiente {0}: {1}").format(
					self.modo, ", ".join(faltantes)
				)
			)

	def _llaves_del_modo(self) -> dict:
		p = "sandbox" if self.modo == "Sandbox" else "prod"
		return {
			"Llave pública": self.get(f"{p}_public_key"),
			"Llave privada": self.get_password(f"{p}_private_key", raise_exception=False),
			"Secreto de integridad": self.get_password(f"{p}_integrity_key", raise_exception=False),
			"Secreto de eventos": self.get_password(f"{p}_events_key", raise_exception=False),
		}

	@property
	def prefijo(self) -> str:
		return "sandbox" if self.modo == "Sandbox" else "prod"

	@property
	def public_key(self) -> str:
		return self.get(f"{self.prefijo}_public_key") or ""

	@property
	def private_key(self) -> str:
		return self.get_password(f"{self.prefijo}_private_key", raise_exception=False) or ""

	@property
	def integrity_key(self) -> str:
		return self.get_password(f"{self.prefijo}_integrity_key", raise_exception=False) or ""

	@property
	def events_key(self) -> str:
		return self.get_password(f"{self.prefijo}_events_key", raise_exception=False) or ""

	@property
	def api_url(self) -> str:
		return URL_API[self.modo]


def get_settings() -> WompiSettings:
	return frappe.get_cached_doc("Wompi Settings")
