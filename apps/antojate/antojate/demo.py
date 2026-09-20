# Copyright (c) 2026, Avantive
# For license information, please see license.txt

"""Datos de demostración.

Deja el sitio listo para mostrárselo al cliente: compañía, catálogo con
variantes, existencias y ciudades de envío. Es idempotente, así que se puede
correr varias veces sin duplicar nada.

    bench --site antojate.localhost execute antojate.demo.cargar
"""

import frappe
from frappe.utils import nowdate

ABREVIATURA = "ANT"
COMPANIA = "Antójate"

CATEGORIAS = ["Café", "Dulces", "Ropa", "Accesorios"]

ATRIBUTOS = {
	"Sabor": ["Amargo", "Leche", "Almendras"],
	"Talla": ["S", "M", "L"],
}

# (código, nombre, categoría, precio, stock, atributo o None, descripción)
PRODUCTOS = [
	("CAFE-500", "Café de origen Huila 500 g", "Café", 38000, 40, None,
	 "Tostión media, notas a panela y naranja. Molido o en grano."),
	("CAFE-TOLIMA", "Café Tolima edición especial 340 g", "Café", 46000, 18, None,
	 "Lote pequeño de finca. Acidez cítrica y cuerpo sedoso."),
	("CHOCO-ART", "Chocolate artesanal 80 g", "Dulces", 14500, 0, "Sabor",
	 "Cacao colombiano fino de aroma, endulzado con panela."),
	("BROWNIE-6", "Caja de brownies x6", "Dulces", 32000, 25, None,
	 "Horneados el mismo día del despacho. Sin conservantes."),
	("CAMISETA", "Camiseta Antójate", "Ropa", 59000, 0, "Talla",
	 "Algodón 100% peinado, estampado serigrafiado a mano."),
	("TERMO-500", "Termo de acero 500 ml", "Accesorios", 72000, 15, None,
	 "Doble pared al vacío: 12 horas caliente, 24 frío."),
	("MUG-CER", "Mug de cerámica esmaltada", "Accesorios", 34000, 30, None,
	 "Hecho a mano, 350 ml. Apto para microondas."),
]

CIUDADES = [
	("Medellín", "Antioquia", 9000, 2, 150000),
	("Bogotá", "Cundinamarca", 12000, 3, 180000),
	("Cali", "Valle del Cauca", 12000, 3, 180000),
	("Barranquilla", "Atlántico", 15000, 4, 200000),
	("Bucaramanga", "Santander", 13000, 3, 180000),
	("Pereira", "Risaralda", 10000, 2, 150000),
]


def cargar():
	"""Punto de entrada. Corre todo en orden."""
	# Frappe 16.17.5 tiene un fallo en frappe/locale.py: get_locale_value deja
	# `value` sin asignar cuando no hay idioma en el contexto, y el asistente de
	# ERPNext lo dispara al construir los globals de safe_exec. Fijar el idioma
	# antes lo evita. Se puede quitar cuando el fallo esté corregido aguas arriba.
	if not getattr(frappe.local, "lang", None):
		frappe.local.lang = "en"

	configurar_erpnext()
	crear_categorias()
	crear_atributos()
	crear_productos()
	crear_ciudades()
	configurar_formato_colombiano()
	configurar_tienda()
	configurar_cobros()
	frappe.db.commit()
	print("\nListo. Entrá a http://antojate.localhost:8080/tienda")


# ---------------------------------------------------------------------------


def configurar_erpnext():
	if frappe.db.exists("Company", COMPANIA):
		marcar_configuracion_terminada()
		print("· Compañía ya existe")
		return

	print("· Corriendo el asistente de configuración de ERPNext (tarda un poco)")
	from erpnext.setup.setup_wizard.setup_wizard import setup_complete

	# setup_complete accede a los argumentos por atributo, no por clave.
	setup_complete(
		frappe._dict(
			{
				"currency": "COP",
				"full_name": "Administrador Antójate",
				"company_name": COMPANIA,
				"company_abbr": ABREVIATURA,
				"timezone": "America/Bogota",
				"country": "Colombia",
				"language": "es",
				"chart_of_accounts": "Standard with Numbers",
				"fy_start_date": f"{nowdate()[:4]}-01-01",
				"fy_end_date": f"{nowdate()[:4]}-12-31",
			}
		)
	)
	marcar_configuracion_terminada()
	print("· Compañía creada")


def marcar_configuracion_terminada():
	"""Deja el sitio sin el asistente de configuración.

	En Frappe v16 `is_setup_complete()` no mira System Settings: recorre el
	doctype `Installed Application` y exige que frappe y erpnext tengan su
	propia bandera en 1. Si no, el escritorio manda al asistente en cada
	ingreso, y el cliente nunca llega a su tienda.
	"""
	for app in ("frappe", "erpnext"):
		nombre = frappe.db.get_value("Installed Application", {"app_name": app})
		if nombre:
			frappe.db.set_value("Installed Application", nombre, "is_setup_complete", 1)

	frappe.db.set_single_value("System Settings", "setup_complete", 1)
	frappe.clear_cache()


def crear_categorias():
	for nombre in CATEGORIAS:
		if not frappe.db.exists("Item Group", nombre):
			frappe.get_doc(
				{
					"doctype": "Item Group",
					"item_group_name": nombre,
					"parent_item_group": "All Item Groups",
					"is_group": 0,
				}
			).insert(ignore_permissions=True)
		frappe.db.set_value("Item Group", nombre, "antojate_publicado", 1)
	print(f"· {len(CATEGORIAS)} categorías")


def crear_atributos():
	for nombre, valores in ATRIBUTOS.items():
		if frappe.db.exists("Item Attribute", nombre):
			continue
		frappe.get_doc(
			{
				"doctype": "Item Attribute",
				"attribute_name": nombre,
				"item_attribute_values": [
					{"attribute_value": v, "abbr": v[:3].upper()} for v in valores
				],
			}
		).insert(ignore_permissions=True)
	print(f"· {len(ATRIBUTOS)} atributos de variante")


def crear_productos():
	cfg_bodega = _bodega()
	creados = 0

	for code, nombre, grupo, precio, stock, atributo, descripcion in PRODUCTOS:
		if not frappe.db.exists("Item", code):
			doc = frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": code,
					"item_name": nombre,
					"item_group": grupo,
					"stock_uom": "Nos",
					"is_stock_item": 1,
					"is_sales_item": 1,
					"description": descripcion,
					"has_variants": 1 if atributo else 0,
				}
			)
			if atributo:
				doc.append("attributes", {"attribute": atributo})
			doc.insert(ignore_permissions=True)
			creados += 1

		frappe.db.set_value(
			"Item",
			code,
			{
				"antojate_publicado": 1,
				"antojate_descripcion_larga": f"<p>{descripcion}</p>",
				"antojate_destacado": 1 if code in ("CAFE-500", "BROWNIE-6") else 0,
			},
		)

		if atributo:
			_crear_variantes(code, atributo, precio, cfg_bodega)
		else:
			_precio(code, precio)
			_stock(code, stock, precio, cfg_bodega)

	print(f"· {len(PRODUCTOS)} productos ({creados} nuevos)")


def _crear_variantes(plantilla: str, atributo: str, precio_base: float, bodega: str):
	from erpnext.controllers.item_variant import create_variant

	for i, valor in enumerate(ATRIBUTOS[atributo]):
		code = f"{plantilla}-{valor[:3].upper()}"
		if not frappe.db.exists("Item", code):
			variante = create_variant(plantilla, {atributo: valor})
			variante.item_code = code
			variante.insert(ignore_permissions=True)

		frappe.db.set_value("Item", code, "antojate_publicado", 1)
		# Precio escalonado para que la ficha muestre un "desde" con sentido.
		precio = precio_base + (i * 2000)
		_precio(code, precio)
		_stock(code, 12 - (i * 2), precio, bodega)


def _precio(code: str, valor: float):
	existente = frappe.db.get_value(
		"Item Price", {"item_code": code, "price_list": "Standard Selling"}, "name"
	)
	if existente:
		frappe.db.set_value("Item Price", existente, "price_list_rate", valor)
		return
	frappe.get_doc(
		{
			"doctype": "Item Price",
			"item_code": code,
			"price_list": "Standard Selling",
			"selling": 1,
			"price_list_rate": valor,
		}
	).insert(ignore_permissions=True)


def _stock(code: str, cantidad: int, valoracion: float, bodega: str):
	if cantidad <= 0:
		return
	from erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry import get_previous_sle

	if get_previous_sle({"item_code": code, "warehouse": bodega, "posting_date": nowdate(), "posting_time": "23:59:59"}):
		return  # ya tiene movimientos: no volvemos a inflar el inventario

	entrada = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": COMPANIA,
			"items": [
				{
					"item_code": code,
					"qty": cantidad,
					"t_warehouse": bodega,
					"basic_rate": valoracion * 0.6,
				}
			],
		}
	)
	entrada.insert(ignore_permissions=True)
	entrada.submit()


def _bodega() -> str:
	nombre = f"Stores - {ABREVIATURA}"
	if frappe.db.exists("Warehouse", nombre):
		return nombre
	# Si el plan de cuentas creó otro nombre, tomamos la primera bodega hoja.
	return frappe.db.get_value("Warehouse", {"company": COMPANIA, "is_group": 0}, "name")


def crear_ciudades():
	for ciudad, depto, costo, dias, gratis in CIUDADES:
		if frappe.db.exists("Antojate Ciudad Envio", ciudad):
			continue
		frappe.get_doc(
			{
				"doctype": "Antojate Ciudad Envio",
				"ciudad": ciudad,
				"departamento": depto,
				"costo": costo,
				"dias_entrega": dias,
				"envio_gratis_desde": gratis,
				"activo": 1,
			}
		).insert(ignore_permissions=True)
	print(f"· {len(CIUDADES)} ciudades de envío")


def configurar_formato_colombiano():
	"""Formato de números y fechas como se usa en Colombia.

	Sin esto los precios salen como $ 38,000.00 en vez de $ 38.000, que es lo
	que el comprador espera ver.
	"""
	ajustes = frappe.get_single("System Settings")
	# `language` es obligatorio y el sitio nace sin él. Además, que falte es lo
	# que dispara el fallo de frappe/locale.py descrito en cargar().
	ajustes.language = "es"
	ajustes.number_format = "#.###,##"
	ajustes.currency_precision = "0"
	ajustes.date_format = "dd-mm-yyyy"
	ajustes.time_zone = "America/Bogota"
	ajustes.country = "Colombia"
	ajustes.save(ignore_permissions=True)

	# El idioma del escritorio lo manda el usuario, no System Settings: sin
	# esto el cliente ve el ERP en inglés aunque el sitio esté en español.
	for usuario in frappe.get_all("User", filters={"enabled": 1}, pluck="name"):
		frappe.db.set_value("User", usuario, "language", "es", update_modified=False)

	print("· Formato colombiano aplicado")


def configurar_cobros():
	"""Deja lista la contabilidad del cobro en línea.

	Sin esto el pedido igual se confirma cuando el pago entra, pero no se crea
	el Payment Entry y al contador le toca conciliar a mano.
	"""
	if not frappe.db.exists("Mode of Payment", "Wompi"):
		frappe.get_doc(
			{
				"doctype": "Mode of Payment",
				"mode_of_payment": "Wompi",
				"type": "Bank",
			}
		).insert(ignore_permissions=True)

	# Wompi dispersa al siguiente día hábil: hasta que el dinero llegue al banco,
	# vive en una cuenta puente. Aquí tomamos la cuenta de banco por defecto.
	cuenta = frappe.db.get_value(
		"Account",
		{"company": COMPANIA, "account_type": ["in", ("Bank", "Cash")], "is_group": 0},
		"name",
		order_by="account_type asc, name asc",
	)

	cfg = frappe.get_single("Wompi Settings")
	cfg.mode_of_payment = "Wompi"
	cfg.paid_to = cuenta
	cfg.modo = "Sandbox"
	# Se deja apagado a propósito: `validate` exige las cuatro llaves cuando
	# está activo, y todavía no las tenemos. Se enciende al cargarlas.
	cfg.enabled = 0
	cfg.save(ignore_permissions=True)
	print(f"· Cobros configurados (cuenta: {cuenta})")


def configurar_tienda():
	cfg = frappe.get_single("Antojate Settings")
	cfg.nombre_tienda = COMPANIA
	cfg.moneda = "COP"
	cfg.company = COMPANIA
	cfg.warehouse = _bodega()
	cfg.price_list = "Standard Selling"
	cfg.customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
	cfg.territory = frappe.db.get_value("Territory", {"is_group": 0}, "name")
	cfg.mostrar_sin_stock = 1
	cfg.productos_por_pagina = 24
	cfg.whatsapp = "573001234567"
	# Las cuentas de ingreso se identifican por root_type, no por account_type:
	# account_type queda vacío en buena parte del plan de cuentas estándar.
	cfg.cuenta_envio = frappe.db.get_value(
		"Account",
		{"company": COMPANIA, "root_type": "Income", "is_group": 0},
		"name",
		order_by="name asc",
	)
	cfg.save(ignore_permissions=True)
	print("· Configuración de la tienda lista")
