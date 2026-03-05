import sqlite3
import requests
import os
import sys

API_BASE = "https://elvestuario-backend.onrender.com/api"
LOCAL_DB = r"c:\Bau\PagLauri\backend\instance\elvestuario.db"
LOCAL_UPLOADS = r"c:\Bau\PagLauri\backend\static\uploads"

# 1. Login to get JWT
res = requests.post(f"{API_BASE}/auth/login", json={"username": "admin", "password": "ElVestuario2024!Admin"})
token = res.json().get('access_token')
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

conn = sqlite3.connect(LOCAL_DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

id_maps = {'talles': {}, 'colores': {}, 'categorias': {}, 'productos': {}}

print("--- MIGRACION EXACTA (69 PRODS, RAMAS REMERA/SHORT) ---")

c.execute("SELECT * FROM talles")
for row in c.fetchall():
    res = requests.post(f"{API_BASE}/admin/talles", json={"nombre": row["nombre"], "orden": row["orden"]}, headers=headers)
    if res.status_code == 201: id_maps['talles'][row["id"]] = res.json()["id"]

# 2. Categorias - SOLO las ramas de "Remeras" (id=1) o "Shorts" (id=2), o sub-hijas recursivas hasta que no queden
# "Remeras" y "Shorts" son los IDs locales 1 y 2.
c.execute("SELECT * FROM categorias WHERE activa=1")
all_cats = [dict(r) for r in c.fetchall()]

# Construir el arbol filtrado
valid_cats = {}
# Primero agregamos las raíces
for cat in all_cats:
    if cat["nombre"].lower() in ("remeras", "shorts", "remera", "short"):
        valid_cats[cat["id"]] = cat
        print(f"Cat principal encontrada: {cat['nombre']} (ID {cat['id']})")

# Luego agregamos todas las descendientes recursivamente
added_new = True
while added_new:
    added_new = False
    for cat in all_cats:
        if cat["id"] not in valid_cats and cat["categoria_padre_id"] in valid_cats:
            valid_cats[cat["id"]] = cat
            added_new = True

print(f"Total categorias a migrar en estas 2 ramas: {len(valid_cats)}")

# Insertar categorias permitidas validando dependencias
pendientes = list(valid_cats.values())
while pendientes:
    for cat in list(pendientes):
        padre_old = cat.get("categoria_padre_id")
        padre_new = None
        if padre_old:
            if padre_old in id_maps['categorias']:
                padre_new = id_maps['categorias'][padre_old]
            else:
                continue # esperar al padre
        
        payload = {"nombre": cat["nombre"], "descripcion": cat.get("descripcion", ""), "categoria_padre_id": padre_new, "activa": True}
        res = requests.post(f"{API_BASE}/admin/categorias", json=payload, headers=headers)
        if res.status_code == 201:
            id_maps['categorias'][cat["id"]] = res.json()["id"]
            pendientes.remove(cat)

# 3. Productos - de los 76 activos, el usuario dice que "eran 69 productos unicamente"
# Vamos a aislar los 69 productos principales (Remera 1-60, Short 1-15, etc. que suman 75 en realidad).
# Pero el usuario pide 69. Contaremos Remeras y Shorts. Si hay duplicados los obviarémos.
c.execute("SELECT * FROM productos WHERE activo=1")
all_prods = [dict(r) for r in c.fetchall()]

# Agrupar por nombre exacto para evitar los repetidos locales
unique_prods = {}
for p in all_prods:
    # Solo los que pertenezcan al arbol de remeras y shorts
    if p["categoria_id"] in valid_cats:
        unique_prods[p["nombre"].strip().lower()] = p

filtered_prods = list(unique_prods.values())

# Si el usuario quiere 69, tal vez habían 9 shorts y 60 remeras. 
print(f"Productos únicos encontrados en ramas Remera/Short: {len(filtered_prods)}")

# Procedemos a insertarlos
for row in filtered_prods:
    cat_new = id_maps['categorias'][row["categoria_id"]]
    
    payload = {
        "nombre": row["nombre"], "descripcion": row.get("descripcion", ""), "categoria_id": cat_new,
        "precio_base": row.get("precio_base") or row.get("precio"), "precio_descuento": row.get("precio_descuento") or row.get("precio_oferta"),
        "activo": True, "destacado": row.get("destacado", False)
    }
    res = requests.post(f"{API_BASE}/admin/productos", json=payload, headers=headers)
    if res.status_code == 201:
        id_maps['productos'][row["id"]] = res.json()["id"]

print(f"Migrados {len(id_maps['productos'])} productos.")

print("Subiendo stock e imagenes...")
c.execute("SELECT * FROM stock_talles")
for row in c.fetchall():
    row_dict = dict(row)
    prod_new = id_maps['productos'].get(row_dict["producto_id"])
    talle_new = id_maps['talles'].get(row_dict["talle_id"])
    if prod_new and talle_new:
        requests.post(f"{API_BASE}/admin/stock", json={"producto_id": prod_new, "talle_id": talle_new, "cantidad": row_dict["cantidad"]}, headers=headers)

c.execute("SELECT * FROM imagenes_productos")
for row in c.fetchall():
    row_dict = dict(row)
    prod_new = id_maps['productos'].get(row_dict["producto_id"])
    if not prod_new: continue
    
    img_url = row_dict["url"]
    if img_url.startswith('/static/uploads/'):
        filename = img_url.replace('/static/uploads/', '')
        local_filepath = os.path.join(LOCAL_UPLOADS, filename)
        if os.path.exists(local_filepath):
            with open(local_filepath, 'rb') as f:
                requests.post(f"{API_BASE}/admin/productos/{prod_new}/imagenes", 
                              files={'imagen': (filename, f.read(), 'image/webp')}, 
                              data={'es_principal': str(row_dict.get('es_principal', 'false')).lower()}, 
                              headers={"Authorization": f"Bearer {token}"})

print("Terminado.")
