app_name = "antojate"
app_title = "Antojate"
app_publisher = "Avantive"
app_description = "Tienda en línea de Antójate sobre Frappe/ERPNext"
app_email = "alexis@avantive.co"
app_license = "mit"

required_apps = ["erpnext"]

# Estilos del storefront público (no del escritorio de Frappe).
# El JS no se incluye por acá: Frappe lo pondría al final del <body>, después
# de los scripts de cada página, que lo necesitan ya cargado. Se incluye en el
# <head> desde templates/tienda_base.html.
web_include_css = "/assets/antojate/css/tienda.css"

# Nota sobre el webhook de Wompi: llega sin sesión iniciada, así que se expone
# con @frappe.whitelist(allow_guest=True). Su autenticidad NO se confía al
# CSRF (Frappe no lo exige a peticiones de invitado) sino al checksum firmado
# que Wompi incluye en el evento y que el endpoint verifica antes de tocar nada.

after_install = "antojate.install.after_install"

# Rutas del storefront. La ficha de producto es dinámica: /producto/<código>.
website_route_rules = [
	{"from_route": "/producto/<item_code>", "to_route": "producto"},
	{"from_route": "/categoria/<item_group>", "to_route": "tienda"},
	{"from_route": "/pedido/<name>", "to_route": "pedido"},
]

# Funciones que las plantillas del storefront pueden llamar directamente.
jinja = {"methods": ["antojate.utils.pesos"]}
