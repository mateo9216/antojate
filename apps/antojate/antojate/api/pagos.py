# Copyright (c) 2026, Avantive
# For license information, please see license.txt

"""Cobro en línea con Wompi.

Dos piezas:

1. `crear_cobro` arma la URL del Checkout Web firmada. El monto se toma del
   Sales Order, nunca del navegador, y va firmado con el secreto de integridad
   para que no se pueda alterar en el camino.

2. `webhook_wompi` recibe la confirmación. Es la ÚNICA fuente de verdad sobre
   si un pedido quedó pagado: el regreso del comprador al sitio no se cree,
   porque esa URL la puede escribir cualquiera a mano.
"""

import hashlib
import json

import frappe
from frappe import _
from frappe.utils import flt, get_url, nowdate

from antojate.antojate.doctype.wompi_settings.wompi_settings import (
	URL_CHECKOUT,
	get_settings,
)

ESTADOS_FINALES = {"APPROVED", "DECLINED", "VOIDED", "ERROR"}


def firma_de_integridad(referencia: str, monto_en_centavos: int, moneda: str, secreto: str) -> str:
	"""SHA256 de referencia + monto + moneda + secreto, en ese orden exacto.

	Cualquier cambio de orden produce una firma que Wompi rechaza.
	"""
	cadena = f"{referencia}{monto_en_centavos}{moneda}{secreto}"
	return hashlib.sha256(cadena.encode("utf-8")).hexdigest()


def crear_cobro(sales_order: str) -> dict:
	"""Registra el intento de pago y devuelve a dónde mandar al comprador."""
	cfg = get_settings()
	if not cfg.enabled:
		frappe.throw(_("Los cobros en línea están desactivados."))

	so = frappe.get_doc("Sales Order", sales_order)
	monto = flt(so.grand_total)
	if monto <= 0:
		frappe.throw(_("El pedido no tiene un total válido para cobrar."))

	moneda = so.currency or "COP"
	# Wompi trabaja en centavos, también para pesos colombianos.
	monto_en_centavos = int(round(monto * 100))

	# Referencia nueva en cada intento: Wompi no acepta reusar la de una
	# transacción que ya falló.
	referencia = f"{so.name}-{frappe.generate_hash(length=6).upper()}"

	txn = frappe.get_doc(
		{
			"doctype": "Wompi Transaction",
			"referencia": referencia,
			"sales_order": so.name,
			"estado": "PENDING",
			"monto": monto,
			"moneda": moneda,
			"email_comprador": so.get("contact_email"),
		}
	).insert(ignore_permissions=True)

	firma = firma_de_integridad(referencia, monto_en_centavos, moneda, cfg.integrity_key)

	params = {
		"public-key": cfg.public_key,
		"currency": moneda,
		"amount-in-cents": monto_en_centavos,
		"reference": referencia,
		"signature:integrity": firma,
		"redirect-url": get_url(f"/pedido/{so.name}?t={so.get('antojate_token') or ''}"),
	}
	if so.get("contact_email"):
		params["customer-data:email"] = so.contact_email

	return {
		"url": f"{URL_CHECKOUT}?{frappe.utils.urlencode(params)}",
		"referencia": referencia,
		"transaccion": txn.name,
	}


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------


def _valor_en_ruta(datos: dict, ruta: str):
	"""Lee 'transaction.amount_in_cents' dentro del dict de datos del evento."""
	actual = datos
	for parte in ruta.split("."):
		if not isinstance(actual, dict):
			return None
		actual = actual.get(parte)
	return actual


def checksum_esperado(evento: dict, secreto: str) -> str:
	"""Recalcula el checksum del evento tal como lo arma Wompi.

	Se concatenan los valores de las propiedades que el propio evento lista en
	`signature.properties`, en ese orden, luego el timestamp y luego el secreto
	de eventos. No se asume qué propiedades son: se leen del evento.
	"""
	firma = evento.get("signature") or {}
	propiedades = firma.get("properties") or []
	datos = evento.get("data") or {}

	cadena = "".join(str(_valor_en_ruta(datos, ruta)) for ruta in propiedades)
	cadena += str(evento.get("timestamp", ""))
	cadena += secreto
	return hashlib.sha256(cadena.encode("utf-8")).hexdigest()


@frappe.whitelist(allow_guest=True)
def webhook_wompi():
	"""Confirmación de pago enviada por Wompi.

	Solo se encarga de leer la petición HTTP; la lógica vive en
	`procesar_evento`, que así se puede probar sin levantar un servidor.
	"""
	try:
		evento = json.loads(frappe.request.get_data(as_text=True) or "{}")
	except json.JSONDecodeError:
		frappe.local.response["http_status_code"] = 400
		return {"error": "json inválido"}

	resultado = procesar_evento(evento, frappe.get_request_header("X-Event-Checksum", ""))
	if resultado.get("error"):
		frappe.local.response["http_status_code"] = resultado.pop("codigo", 400)
	return resultado


def procesar_evento(evento: dict, checksum_header: str = "") -> dict:
	"""Valida y aplica un evento de Wompi.

	Wompi reintenta hasta 3 veces en 24 h si no recibe un 200, así que esto
	tiene que ser idempotente y responder 200 incluso ante un evento repetido.
	"""
	import hmac

	cfg = get_settings()
	recibido = (evento.get("signature") or {}).get("checksum") or checksum_header
	esperado = checksum_esperado(evento, cfg.events_key)

	# Comparación en tiempo constante: evita filtrar el secreto por el tiempo
	# que tarda en fallar la comparación.
	if not recibido or not hmac.compare_digest(str(recibido).lower(), esperado.lower()):
		frappe.log_error(
			title="Wompi: checksum inválido",
			message=f"Evento rechazado.\nRecibido: {recibido}\nEsperado: {esperado}\n\n{evento}",
		)
		return {"error": "checksum inválido", "codigo": 401}

	if evento.get("event") != "transaction.updated":
		# Otros eventos (tokens de Nequi, etc.) todavía no nos interesan, pero
		# hay que responder 200 o Wompi los reintenta.
		return {"ok": True, "ignorado": evento.get("event")}

	transaccion = (evento.get("data") or {}).get("transaction") or {}
	referencia = transaccion.get("reference")
	if not referencia:
		return {"ok": True, "ignorado": "evento sin referencia"}

	frappe.set_user("Administrator")
	_aplicar_evento(referencia, transaccion, evento)
	return {"ok": True}


def _aplicar_evento(referencia: str, transaccion: dict, evento: dict) -> None:
	if not frappe.db.exists("Wompi Transaction", referencia):
		frappe.log_error(
			title="Wompi: referencia desconocida",
			message=f"Llegó un evento para {referencia}, que no existe en el sistema.",
		)
		return

	# FOR UPDATE: si Wompi manda el mismo evento dos veces a la vez, la segunda
	# espera a que la primera termine y encuentra procesado=1.
	txn = frappe.get_doc("Wompi Transaction", referencia, for_update=True)

	if txn.procesado:
		return

	estado = transaccion.get("status") or "ERROR"
	txn.estado = estado
	txn.transaction_id = transaccion.get("id")
	txn.metodo_pago = transaccion.get("payment_method_type")
	txn.payload = json.dumps(evento, indent=2, ensure_ascii=False)

	if estado in ESTADOS_FINALES:
		txn.procesado = 1

	txn.save(ignore_permissions=True)

	if estado == "APPROVED":
		_confirmar_pedido(txn, transaccion)
	elif estado in ("DECLINED", "VOIDED", "ERROR"):
		_liberar_pedido(txn)


	frappe.db.commit()


def _confirmar_pedido(txn, transaccion: dict) -> None:
	"""El pago entró: se confirma el pedido y se registra el ingreso."""
	so = frappe.get_doc("Sales Order", txn.sales_order)

	# Defensa de último nivel: que lo cobrado coincida con lo que vale el
	# pedido. Si no coincide, se confirma nada y queda constancia.
	cobrado = flt(transaccion.get("amount_in_cents", 0)) / 100
	if abs(cobrado - flt(so.grand_total)) > 1:
		frappe.log_error(
			title="Wompi: el monto pagado no coincide con el pedido",
			message=f"Pedido {so.name}: vale {so.grand_total}, se pagó {cobrado}.",
		)
		return

	if so.docstatus == 0:
		try:
			so.submit()
		except Exception:
			# El comprador ya pagó. Que el pedido no se pueda confirmar (por
			# ejemplo, porque alguien vendió el último en otra parte) es un
			# problema que alguien tiene que resolver a mano, no algo que se
			# pueda descartar en silencio.
			frappe.log_error(
				title="Wompi: pago recibido pero el pedido no se pudo confirmar",
				message=(
					f"Pedido {so.name}, transacción {txn.referencia}. "
					f"El dinero entró. Revisar y confirmar manualmente.\n\n"
					f"{frappe.get_traceback()}"
				),
			)
			return

	_registrar_pago(so, txn)


def _registrar_pago(so, txn) -> None:
	"""Crea el Payment Entry contra el pedido.

	Si la contabilidad no está configurada todavía (falta cuenta de banco o
	modo de pago), no se rompe el pedido: queda registrado el error para que
	el contador lo concilie. El comprador ya pagó y su pedido está confirmado,
	que es lo que no puede fallar.
	"""
	cfg = frappe.get_cached_doc("Wompi Settings")
	if not cfg.get("mode_of_payment") or not cfg.get("paid_to"):
		frappe.log_error(
			title="Wompi: falta configurar la contabilidad del cobro",
			message=(
				f"El pedido {so.name} se confirmó y está pagado, pero no se creó el "
				"Payment Entry porque en Wompi Settings faltan el modo de pago o la "
				"cuenta de banco. Conciliar a mano."
			),
		)
		return

	try:
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		pe = get_payment_entry("Sales Order", so.name)
		pe.mode_of_payment = cfg.mode_of_payment
		pe.paid_to = cfg.paid_to
		pe.reference_no = txn.transaction_id or txn.referencia
		pe.reference_date = nowdate()
		pe.insert(ignore_permissions=True)
		pe.submit()
	except Exception:
		frappe.log_error(
			title="Wompi: no se pudo crear el Payment Entry",
			message=f"Pedido {so.name}, transacción {txn.referencia}\n\n{frappe.get_traceback()}",
		)


def _liberar_pedido(txn) -> None:
	"""El pago no entró.

	No hay nada que deshacer: un Sales Order en borrador no reserva inventario
	ni toca la contabilidad, así que se deja como está. Forzarle el estado
	`Closed` lo dejaría en un estado que ERPNext no considera válido mientras
	esté en borrador, y ensuciaría los informes.

	El pedido queda como un borrador abandonado y el intento fallido queda
	registrado en su `Wompi Transaction`. El comprador puede reintentar el pago
	desde la página de su pedido, que reusa este mismo borrador.
	"""
	return


@frappe.whitelist(allow_guest=True)
def reintentar_pago(pedido: str, token: str) -> dict:
	"""Genera un cobro nuevo para un pedido que no se alcanzó a pagar.

	Wompi no permite reusar la referencia de una transacción fallida, así que
	`crear_cobro` arma una nueva. Solo se permite sobre pedidos en borrador:
	uno ya confirmado está pagado y no se vuelve a cobrar.
	"""
	so = _pedido_del_comprador(pedido, token)
	if so.docstatus != 0:
		frappe.throw(_("Este pedido ya no está pendiente de pago."))
	return crear_cobro(so.name)


def _pedido_del_comprador(pedido: str, token: str):
	"""Carga un pedido validando el token que lleva el comprador.

	Los nombres de pedido son consecutivos, así que sin esta comprobación
	cualquiera vería los pedidos ajenos probando números.
	"""
	import hmac

	guardado = frappe.db.get_value("Sales Order", pedido, "antojate_token")
	if not guardado or not token or not hmac.compare_digest(str(guardado), str(token)):
		raise frappe.DoesNotExistError

	return frappe.get_doc("Sales Order", pedido)
