import requests

API_BASE = "https://elvestuario-backend.onrender.com/api"

# 1. Login to get JWT
print("Authentication...")
res = requests.post(f"{API_BASE}/auth/login", json={
    "username": "admin",
    "password": "ElVestuario2024!Admin"
})
if res.status_code != 200:
    print("Failed to login!", res.text)
    exit(1)
    
token = res.json().get('access_token')
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 2. Nuke everything
print("\n--- LIMPIEZA TOTAL ---")
prods_res = requests.get(f"{API_BASE}/productos?page=1&page_size=1000")
if prods_res.status_code == 200:
    prods = prods_res.json().get('items', [])
    for p in prods:
        requests.delete(f"{API_BASE}/admin/productos/{p['id']}", headers=headers)
        print(f"Borrando prod {p['id']} - {p['nombre']}")

cats_res = requests.get(f"{API_BASE}/categorias")
if cats_res.status_code == 200:
    cats = cats_res.json()
    all_cats = []
    def flatten(c_list):
        for c in c_list:
            all_cats.append(c)
            if c.get("subcategorias"):
                flatten(c["subcategorias"])
    flatten(cats)
    all_cats.sort(key=lambda x: x["id"], reverse=True)
    for c in all_cats:
        requests.delete(f"{API_BASE}/admin/categorias/{c['id']}", headers=headers)
        print(f"Borrando cat {c['id']} - {c['nombre']}")

talles_res = requests.get(f"{API_BASE}/talles")
if talles_res.status_code == 200:
    for t in talles_res.json():
        if t['nombre'] != '-':  # Avoid deleting default if there's one
            requests.delete(f"{API_BASE}/admin/talles/{t['id']}", headers=headers)

print("\n--- CREACION DE TALLES ---")
talles_creados = {}
talles = ["S", "M", "L", "XL", "XXL"]
for idx, nombre in enumerate(talles):
    res = requests.post(f"{API_BASE}/admin/talles", json={"nombre": nombre, "orden": idx + 1}, headers=headers)
    if res.status_code == 201:
        talles_creados[nombre] = res.json()["id"]
        print(f"Creado talle {nombre} (ID: {talles_creados[nombre]})")

print("\n--- CREACION DE CATEGORIAS ---")
categorias_creadas = {}

def crear_cat(nombre, padre_id=None):
    payload = {"nombre": nombre, "activa": True}
    if padre_id:
        payload["categoria_padre_id"] = padre_id
    res = requests.post(f"{API_BASE}/admin/categorias", json=payload, headers=headers)
    if res.status_code == 201:
        cat_id = res.json()["id"]
        categorias_creadas[nombre] = cat_id
        print(f"Creada categoria {nombre} (ID: {cat_id})")
        return cat_id
    else:
        print(f"Error creando {nombre}: {res.text}")
        return None

cat_remeras = crear_cat("Remeras")
cat_shorts = crear_cat("Shorts")

cat_premier = crear_cat("Premier League", cat_remeras)
cat_laliga = crear_cat("La Liga", cat_remeras)
cat_argentina = crear_cat("Futbol Argentino", cat_remeras)
cat_selecciones = crear_cat("Selecciones", cat_remeras)

cat_short_premier = crear_cat("Premier League", cat_shorts)
cat_short_argentina = crear_cat("Futbol Argentino", cat_shorts)
cat_short_selecciones = crear_cat("Selecciones", cat_shorts)


print("\n--- CREACION DE PRODUCTOS ---")
productos_reales = [
    {"nombre": "Camiseta Liverpool Titular 24/25", "cat": cat_premier, "precio": 45000, "descuento": 39000, "desc": "Camiseta oficial del Liverpool FC, modelo titular de la temporada 2024/2025."},
    {"nombre": "Camiseta Liverpool Suplente 24/25", "cat": cat_premier, "precio": 45000, "descuento": None, "desc": "Camiseta oficial del Liverpool FC temporada 24/25."},
    {"nombre": "Camiseta Manchester City Titular 24/25", "cat": cat_premier, "precio": 45000, "descuento": None, "desc": "Camiseta del City." },
    {"nombre": "Camiseta Real Madrid Titular 24/25", "cat": cat_laliga, "precio": 48000, "descuento": 42000, "desc": "La gloriosa blanca del Real Madrid con detalles dorados."},
    {"nombre": "Camiseta Boca Juniors Titular 2024", "cat": cat_argentina, "precio": 40000, "descuento": None, "desc": "La azul y oro tradicional."},
    {"nombre": "Camiseta River Plate Titular 2024", "cat": cat_argentina, "precio": 40000, "descuento": None, "desc": "El manto sagrado con la banda roja."},
    {"nombre": "Camiseta Argentina Titular Campeón del Mundo", "cat": cat_selecciones, "precio": 55000, "descuento": 49000, "desc": "La camiseta de las 3 estrellas."},
    {"nombre": "Camiseta Argentina Alternativa (Estacionera) 2024", "cat": cat_selecciones, "precio": 52000, "descuento": None, "desc": "Modelo violeta glorioso."},
    
    # Shorts
    {"nombre": "Short Liverpool Titular 24/25", "cat": cat_short_premier, "precio": 25000, "descuento": 22000, "desc": "Short oficial del Liverpool."},
    {"nombre": "Short Real Madrid Titular 24/25", "cat": cat_shorts, "precio": 26000, "descuento": None, "desc": "Short oficial Real Madrid."},
    {"nombre": "Short Boca Juniors Titular 2024", "cat": cat_short_argentina, "precio": 20000, "descuento": None, "desc": "Short azul de Boca."},
    {"nombre": "Short Argentina Titular", "cat": cat_short_selecciones, "precio": 30000, "descuento": None, "desc": "Short negro de la seleccion Argentina con detalles celestes y blancos."}
]

print("Creando productos y su stock...")
for p in productos_reales:
    payload = {
        "nombre": p["nombre"],
        "descripcion": p["desc"],
        "categoria_id": p["cat"],
        "precio_base": p["precio"],
        "precio_descuento": p["descuento"],
        "activo": True,
        "destacado": True if "Argentina" in p["nombre"] or "Liverpool" in p["nombre"] else False
    }
    res = requests.post(f"{API_BASE}/admin/productos", json=payload, headers=headers)
    if res.status_code == 201:
        prod_id = res.json()["id"]
        print(f"[OK] Producto {p['nombre']}")
        
        # Asignar stock en todos los talles creados (10 unidades por defecto)
        for t_nombre, t_id in talles_creados.items():
            stock_res = requests.post(f"{API_BASE}/admin/stock", json={
                "producto_id": prod_id,
                "talle_id": t_id,
                "cantidad": 10
            }, headers=headers)
    else:
        print(f"[ERR] Prod {p['nombre']}: {res.text}")

print("\n¡Semilla ejecutada exitosamente! Base de datos de produccion lista y limpia.")
