# Copyright (c) 2026, Avantive
# For license information, please see license.txt

"""Lectura del catálogo para el storefront.

Todo lo que se muestra al público sale de aquí. Los precios y el stock se leen
siempre de la base en el momento, nunca de lo que mande el navegador.
"""

import frappe
from frappe.utils import cint, flt

from antojate.antojate.doctype.antojate_settings.antojate_settings import get_settings


def _campos_listado():
	return [
		"name as item_code",
		"item_name",
		"item_group",
		"image",
		"has_variants",
		"stock_uom",
		"antojate_orden",
		"antojate_destacado",
	]


def listar_productos(item_group: str | None = None, busqueda: str | None = None, pagina: int = 1):
	"""Productos publicados, paginados.

	Solo devuelve plantillas y productos sueltos: las variantes no se listan
	por separado, se escogen dentro de la ficha del producto.
	"""
	cfg = get_settings()
	por_pagina = cint(cfg.productos_por_pagina) or 24
	pagina = max(1, cint(pagina))

	filtros = {
		"antojate_publicado": 1,
		"disabled": 0,
		"is_sales_item": 1,
		"variant_of": ["is", "not set"],
	}
	if item_group:
		filtros["item_group"] = item_group

	o_filtros = None
	if busqueda:
		termino = f"%{busqueda.strip()}%"
		o_filtros = [
			["Item", "item_name", "like", termino],
			["Item", "name", "like", termino],
		]

	productos = frappe.get_all(
		"Item",
		filters=filtros,
		or_filters=o_filtros,
		fields=_campos_listado(),
		# Frappe v16 solo acepta nombres de campo en order_by, nada de
		# expresiones SQL. Por eso el campo de orden vale 999 por defecto: los
		# productos sin orden asignado caen al final sin necesidad de un CASE.
		order_by="antojate_destacado desc, antojate_orden asc, item_name asc",
		limit_start=(pagina - 1) * por_pagina,
		limit_page_length=por_pagina + 1,
	)

	hay_mas = len(productos) > por_pagina
	productos = productos[:por_pagina]

	for p in productos:
		_decorar(p, cfg)

	return {"productos": productos, "pagina": pagina, "hay_mas": hay_mas}


def _decorar(producto: dict, cfg) -> None:
	"""Agrega precio, stock y ruta a una fila del listado."""
	producto["ruta"] = f"/producto/{frappe.utils.quote(producto['item_code'])}"
	producto["imagen"] = producto.get("image") or "/assets/antojate/img/sin-imagen.svg"

	if producto.get("has_variants"):
		# En una plantilla el precio se muestra como "desde X": es el menor
		# precio entre sus variantes vendibles.
		precios = _precios_de_variantes(producto["item_code"], cfg.price_list)
		producto["precio"] = min(precios) if precios else 0
		producto["desde"] = len(precios) > 1
		producto["disponible"] = bool(precios) and _stock_de_variantes(producto["item_code"], cfg.warehouse) > 0
	else:
		producto["precio"] = precio_de(producto["item_code"], cfg.price_list)
		producto["desde"] = False
		producto["disponible"] = stock_de(producto["item_code"], cfg.warehouse) > 0


def precio_de(item_code: str, price_list: str) -> float:
	"""Precio de venta vigente. 0 si el producto no tiene precio cargado."""
	fila = frappe.get_all(
		"Item Price",
		filters={"item_code": item_code, "price_list": price_list, "selling": 1},
		fields=["price_list_rate"],
		order_by="valid_from desc",
		limit=1,
	)
	return flt(fila[0].price_list_rate) if fila else 0.0


def stock_de(item_code: str, warehouse: str) -> float:
	"""Cantidad realmente vendible: lo que hay menos lo ya reservado.

	Usar actual_qty a secas sobrevende, porque incluye lo comprometido en
	pedidos que todavía no se despachan.
	"""
	fila = frappe.get_all(
		"Bin",
		filters={"item_code": item_code, "warehouse": warehouse},
		fields=["actual_qty", "reserved_qty"],
		limit=1,
	)
	if not fila:
		return 0.0
	return flt(fila[0].actual_qty) - flt(fila[0].reserved_qty)


def _variantes_de(item_code: str) -> list[str]:
	return [
		v.name
		for v in frappe.get_all(
			"Item",
			filters={"variant_of": item_code, "disabled": 0},
			fields=["name"],
		)
	]


def _precios_de_variantes(item_code: str, price_list: str) -> list[float]:
	precios = [precio_de(v, price_list) for v in _variantes_de(item_code)]
	return [p for p in precios if p > 0]


def _stock_de_variantes(item_code: str, warehouse: str) -> float:
	return sum(stock_de(v, warehouse) for v in _variantes_de(item_code))


def obtener_producto(item_code: str) -> dict | None:
	"""Ficha completa de un producto, con sus variantes si las tiene."""
	cfg = get_settings()

	if not frappe.db.exists("Item", {"name": item_code, "antojate_publicado": 1, "disabled": 0}):
		return None

	item = frappe.db.get_value(
		"Item",
		item_code,
		[
			"name as item_code",
			"item_name",
			"item_group",
			"image",
			"description",
			"antojate_descripcion_larga",
			"has_variants",
			"stock_uom",
		],
		as_dict=True,
	)

	item["imagen"] = item.get("image") or "/assets/antojate/img/sin-imagen.svg"
	item["descripcion"] = item.get("antojate_descripcion_larga") or item.get("description") or ""
	item["variantes"] = []
	item["atributos"] = []

	if item["has_variants"]:
		item["variantes"] = _detalle_variantes(item["item_code"], cfg)
		item["atributos"] = _atributos_de(item["item_code"])
		disponibles = [v["precio"] for v in item["variantes"] if v["disponible"]]
		item["precio"] = min(disponibles) if disponibles else 0
		item["disponible"] = bool(disponibles)
	else:
		item["precio"] = precio_de(item["item_code"], cfg.price_list)
		item["disponible"] = stock_de(item["item_code"], cfg.warehouse) > 0

	return item


def _detalle_variantes(item_code: str, cfg) -> list[dict]:
	variantes = []
	for nombre in _variantes_de(item_code):
		atributos = frappe.get_all(
			"Item Variant Attribute",
			filters={"parent": nombre},
			fields=["attribute", "attribute_value"],
			order_by="idx asc",
		)
		stock = stock_de(nombre, cfg.warehouse)
		variantes.append(
			{
				"item_code": nombre,
				"item_name": frappe.db.get_value("Item", nombre, "item_name"),
				"atributos": {a.attribute: a.attribute_value for a in atributos},
				"etiqueta": " / ".join(a.attribute_value for a in atributos),
				"precio": precio_de(nombre, cfg.price_list),
				"stock": stock,
				"disponible": stock > 0,
			}
		)
	return variantes


def _atributos_de(item_code: str) -> list[dict]:
	"""Atributos de la plantilla, en orden, con sus valores posibles."""
	filas = frappe.get_all(
		"Item Variant Attribute",
		filters={"parent": item_code, "parenttype": "Item"},
		fields=["attribute", "idx"],
		order_by="idx asc",
	)
	atributos = []
	for fila in filas:
		valores = frappe.get_all(
			"Item Attribute Value",
			filters={"parent": fila.attribute},
			fields=["attribute_value"],
			order_by="idx asc",
		)
		atributos.append(
			{
				"nombre": fila.attribute,
				"valores": [v.attribute_value for v in valores],
			}
		)
	return atributos


def categorias() -> list[dict]:
	"""Categorías marcadas para mostrarse en la tienda."""
	return frappe.get_all(
		"Item Group",
		filters={"antojate_publicado": 1},
		fields=["name", "item_group_name as nombre", "antojate_orden"],
		order_by="antojate_orden asc, item_group_name asc",
	)
