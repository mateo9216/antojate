# Copyright (c) 2026, Avantive
# For license information, please see license.txt

"""Carrito y creación del pedido.

El carrito vive en el navegador del comprador, pero **nada de lo que manda se
cree**: cada precio, cada existencia y el costo del envío se vuelven a leer de
la base antes de crear el pedido. Del navegador solo se aceptan dos cosas: qué
producto y cuántas unidades.
"""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, cint, flt, nowdate, validate_email_address

from antojate.antojate.doctype.antojate_settings.antojate_settings import get_settings
from antojate.api import catalogo


MAX_LINEAS = 50
MAX_UNIDADES_POR_LINEA = 100


def _normalizar(items) -> list[dict]:
	"""Deja el carrito del navegador en una forma mínima y segura."""
	items = frappe.parse_json(items) or []
	if not isinstance(items, list):
		frappe.throw(_("Carrito inválido."))
	if len(items) > MAX_LINEAS:
		frappe.throw(_("El carrito tiene demasiados productos distintos."))

	limpio = []
	for fila in items:
		if not isinstance(fila, dict):
			continue
		code = (fila.get("item_code") or "").strip()
		qty = cint(fila.get("qty"))
		if not code or qty <= 0:
			continue
		limpio.append({"item_code": code, "qty": min(qty, MAX_UNIDADES_POR_LINEA)})
	return limpio


@frappe.whitelist(allow_guest=True)
def cotizar(items, ciudad: str | None = None) -> dict:
	"""Recalcula el carrito con precios y stock reales. No crea nada."""
	cfg = get_settings()
	lineas, errores = [], []
	subtotal = 0.0

	for fila in _normalizar(items):
		datos = _validar_linea(fila, cfg, errores)
		if datos:
			lineas.append(datos)
			subtotal += datos["subtotal"]

	envio, info_envio = _costo_envio(ciudad, subtotal)

	return {
		"lineas": lineas,
		"errores": errores,
		"subtotal": subtotal,
		"envio": envio,
		"envio_info": info_envio,
		"total": subtotal + envio,
		"moneda": cfg.moneda,
	}


def _validar_linea(fila: dict, cfg, errores: list) -> dict | None:
	code = fila["item_code"]

	item = frappe.db.get_value(
		"Item",
		code,
		["item_name", "image", "has_variants", "antojate_publicado", "disabled"],
		as_dict=True,
	)
	if not item or item.disabled or not item.antojate_publicado:
		errores.append(_("Un producto de tu carrito ya no está disponible y se quitó."))
		return None

	if item.has_variants:
		# Una plantilla no se vende: hay que escoger una variante concreta.
		errores.append(_("Debes escoger una presentación de {0}.").format(item.item_name))
		return None

	precio = catalogo.precio_de(code, cfg.price_list)
	if precio <= 0:
		errores.append(_("{0} no tiene precio y se quitó del carrito.").format(item.item_name))
		return None

	stock = catalogo.stock_de(code, cfg.warehouse)
	qty = fila["qty"]
	recortado = False
	if stock <= 0:
		errores.append(_("{0} se agotó y se quitó del carrito.").format(item.item_name))
		return None
	if qty > stock:
		# int() hacia abajo: con 0,5 unidades disponibles no se puede vender 1.
		qty = int(stock)
		if qty <= 0:
			errores.append(_("{0} no tiene unidades completas disponibles.").format(item.item_name))
			return None
		recortado = True
		errores.append(
			_("Solo quedan {0} unidades de {1}; ajustamos la cantidad.").format(qty, item.item_name)
		)

	return {
		"item_code": code,
		"item_name": item.item_name,
		"imagen": item.image or "/assets/antojate/img/sin-imagen.svg",
		"qty": qty,
		"precio": precio,
		"subtotal": flt(precio * qty, 2),
		"stock": stock,
		"recortado": recortado,
	}


def _costo_envio(ciudad: str | None, subtotal: float) -> tuple[float, dict]:
	if not ciudad:
		return 0.0, {"estado": "sin_ciudad"}

	fila = frappe.db.get_value(
		"Antojate Ciudad Envio",
		{"ciudad": ciudad, "activo": 1},
		["costo", "dias_entrega", "envio_gratis_desde"],
		as_dict=True,
	)
	if not fila:
		return 0.0, {"estado": "no_cubierta", "ciudad": ciudad}

	gratis = flt(fila.envio_gratis_desde) > 0 and subtotal >= flt(fila.envio_gratis_desde)
	return (
		0.0 if gratis else flt(fila.costo),
		{
			"estado": "ok",
			"ciudad": ciudad,
			"dias": cint(fila.dias_entrega),
			"gratis": gratis,
			"falta_para_gratis": max(0.0, flt(fila.envio_gratis_desde) - subtotal)
			if flt(fila.envio_gratis_desde) > 0
			else 0,
		},
	)


@frappe.whitelist(allow_guest=True)
def ciudades() -> list[dict]:
	return frappe.get_all(
		"Antojate Ciudad Envio",
		filters={"activo": 1},
		fields=["ciudad", "departamento", "costo", "dias_entrega"],
		order_by="ciudad asc",
	)


# ---------------------------------------------------------------------------
# Creación del pedido
# ---------------------------------------------------------------------------


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=20, seconds=3600)
def crear_pedido(items, comprador) -> dict:
	"""Crea el Sales Order en borrador y devuelve a dónde ir a pagar.

	El pedido nace en borrador a propósito: solo se confirma cuando Wompi
	avisa que el pago entró. Así un checkout abandonado no ensucia el
	inventario ni la contabilidad.
	"""
	comprador = frappe.parse_json(comprador) or {}
	_validar_comprador(comprador)

	cotizacion = cotizar(items, comprador.get("ciudad"))
	if not cotizacion["lineas"]:
		frappe.throw(_("Tu carrito quedó vacío. Revisá los productos e intentá de nuevo."))
	if cotizacion["envio_info"]["estado"] == "no_cubierta":
		frappe.throw(_("Todavía no hacemos envíos a {0}.").format(comprador.get("ciudad")))

	cfg = get_settings()

	# Ignoramos permisos a propósito: el comprador es un invitado y no puede
	# crear clientes ni pedidos por sí mismo. Lo que protege esta función no
	# son los permisos de Frappe sino la validación de arriba.
	cliente = _cliente_para(comprador, cfg)

	so = frappe.new_doc("Sales Order")
	so.customer = cliente
	so.company = cfg.company
	so.currency = cfg.moneda
	so.selling_price_list = cfg.price_list
	so.transaction_date = nowdate()
	so.delivery_date = add_days(nowdate(), cotizacion["envio_info"].get("dias") or 3)
	so.contact_email = comprador.get("email")
	so.antojate_telefono = comprador.get("telefono")
	# Con esto el comprador ve su pedido sin tener cuenta, y nadie más puede
	# verlo probando números de pedido consecutivos.
	so.antojate_token = frappe.generate_hash(length=24)

	for linea in cotizacion["lineas"]:
		so.append(
			"items",
			{
				"item_code": linea["item_code"],
				"qty": linea["qty"],
				"rate": linea["precio"],
				"warehouse": cfg.warehouse,
				"delivery_date": so.delivery_date,
			},
		)

	if cotizacion["envio"] > 0:
		if not cfg.cuenta_envio:
			frappe.throw(_("Falta configurar la cuenta contable del flete."))
		so.append(
			"taxes",
			{
				"charge_type": "Actual",
				"account_head": cfg.cuenta_envio,
				"description": _("Envío a {0}").format(comprador.get("ciudad")),
				"tax_amount": cotizacion["envio"],
			},
		)

	so.insert(ignore_permissions=True)

	from antojate.api import pagos

	cobro = pagos.crear_cobro(so.name)
	frappe.db.commit()

	return {"pedido": so.name, "total": so.grand_total, "url_pago": cobro["url"]}


def _validar_comprador(c: dict) -> None:
	faltantes = [
		etiqueta
		for campo, etiqueta in [
			("nombre", _("nombre")),
			("email", _("correo")),
			("telefono", _("teléfono")),
			("ciudad", _("ciudad")),
			("direccion", _("dirección")),
		]
		if not (c.get(campo) or "").strip()
	]
	if faltantes:
		frappe.throw(_("Falta: {0}.").format(", ".join(faltantes)))

	# Lanza si el correo no es válido; sin él no hay cómo avisarle del pedido.
	validate_email_address(c["email"], throw=True)


def _cliente_para(c: dict, cfg) -> str:
	"""Devuelve el Customer del comprador, reusándolo si ya compró antes."""
	email = c["email"].strip().lower()

	existente = frappe.db.get_value(
		"Contact Email", {"email_id": email}, "parent"
	)
	if existente:
		enlace = frappe.db.get_value(
			"Dynamic Link",
			{"parent": existente, "parenttype": "Contact", "link_doctype": "Customer"},
			"link_name",
		)
		if enlace and frappe.db.exists("Customer", enlace):
			_actualizar_direccion(enlace, c)
			return enlace

	cliente = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": c["nombre"].strip(),
			"customer_type": "Individual",
			"customer_group": cfg.customer_group,
			"territory": cfg.territory,
		}
	).insert(ignore_permissions=True)

	contacto = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": c["nombre"].strip(),
			"links": [{"link_doctype": "Customer", "link_name": cliente.name}],
			"email_ids": [{"email_id": email, "is_primary": 1}],
			"phone_nos": [{"phone": c["telefono"].strip(), "is_primary_mobile_no": 1}],
		}
	).insert(ignore_permissions=True)

	cliente.db_set("customer_primary_contact", contacto.name)
	_actualizar_direccion(cliente.name, c)
	return cliente.name


def _actualizar_direccion(cliente: str, c: dict) -> None:
	"""Guarda la dirección de envío de este pedido.

	Se crea una dirección nueva en vez de pisar la anterior: el mismo comprador
	puede mandar pedidos a sitios distintos, y el histórico importa para el
	despacho.
	"""
	frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": f"{c['nombre'].strip()} - {frappe.utils.now()}",
			"address_type": "Shipping",
			"address_line1": c["direccion"].strip(),
			"address_line2": (c.get("detalle_direccion") or "").strip() or None,
			"city": c["ciudad"].strip(),
			"country": "Colombia",
			"phone": c["telefono"].strip(),
			"email_id": c["email"].strip().lower(),
			"links": [{"link_doctype": "Customer", "link_name": cliente}],
		}
	).insert(ignore_permissions=True)
