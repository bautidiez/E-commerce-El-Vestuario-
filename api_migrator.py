import sqlite3
import requests
import time
import os
import io

API_BASE = "https://elvestuario-backend.onrender.com/api"
LOCAL_DB = r"c:\Bau\PagLauri\backend\instance\elvestuario.db"
LOCAL_UPLOADS = r"c:\Bau\PagLauri\backend\static\uploads"

# 1. Login to get JWT
def login():
    res = requests.post(f"{API_BASE}/auth/login", json={
        "username": "admin",
        "password": "ElVestuario2024!Admin"
    })
    if res.status_code == 200:
        return res.json().get('access_token')
    else:
        print("Error login:", res.text)
        return None

def migrate():
    token = login()
    if not token:
        print("No se pudo iniciar sesion. Verifica las credenciales por defecto.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    conn = sqlite3.connect(LOCAL_DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    id_maps = {
        'talles': {},
        'colores': {},
        'categorias': {},
        'productos': {}
    }

    # Fetch existing from API to build maps
    print("--- Obteniendo datos existentes del API ---")
    
    # Talles map
    res = requests.get(f"{API_BASE}/talles")
    live_talles = res.json() if res.status_code == 200 else []
    for t in live_talles:
        # Find corresponding local ID by name
        c.execute("SELECT id FROM talles WHERE nombre = ?", (t["nombre"],))
        local_row = c.fetchone()
        if local_row: id_maps['talles'][local_row["id"]] = t["id"]

    # Colores map
    res = requests.get(f"{API_BASE}/colores")
    live_colores = res.json() if res.status_code == 200 else []
    for co in live_colores:
        c.execute("SELECT id FROM colores WHERE nombre = ?", (co["nombre"],))
        local_row = c.fetchone()
        if local_row: id_maps['colores'][local_row["id"]] = co["id"]

    # Categorias map
    res = requests.get(f"{API_BASE}/categorias")
    live_cats = res.json() if res.status_code == 200 else []
    def map_cats(cats_list):
        for ca in cats_list:
            c.execute("SELECT id FROM categorias WHERE nombre = ?", (ca["nombre"],))
            local_row = c.fetchone()
            if local_row: id_maps['categorias'][local_row["id"]] = ca["id"]
            if "subcategorias" in ca:
                map_cats(ca["subcategorias"])
    map_cats(live_cats)

    # Productos map
    # We might have pagination in /api/productos, let's just search or assume we can get all via admin/products/search?q=
    # Or just use the /api/admin/stock which we have to do anyway. Wait, admin/productos doesn't exist as a pure GET all? There is "GET /api/productos?page=1&page_size=1000"
    res = requests.get(f"{API_BASE}/productos?page=1&page_size=1000")
    live_prods = res.json().get('items', []) if res.status_code == 200 else []
    for p in live_prods:
        c.execute("SELECT id FROM productos WHERE nombre = ?", (p["nombre"],))
        local_row = c.fetchone()
        if local_row: id_maps['productos'][local_row["id"]] = p["id"]

    print(f"Maps cargados: {len(id_maps['talles'])} talles, {len(id_maps['colores'])} colores, {len(id_maps['categorias'])} categorias, {len(id_maps['productos'])} productos")

    # -- 1. Talles
    print("\n--- Migrando Talles ---")
    c.execute("SELECT * FROM talles")
    for row in c.fetchall():
        if row["id"] in id_maps['talles']: continue
        res = requests.post(f"{API_BASE}/admin/talles", json={
            "nombre": row["nombre"],
            "orden": row["orden"]
        }, headers=headers)
        if res.status_code == 201:
            new_talle = res.json()
            id_maps['talles'][row["id"]] = new_talle["id"]
            print(f"[OK] Talle '{row['nombre']}'")
        else:
            print(f"[ERROR] Error talle '{row['nombre']}': {res.text}")

    # -- 2. Colores
    print("\n--- Migrando Colores ---")
    c.execute("SELECT * FROM colores")
    for row in c.fetchall():
        if row["id"] in id_maps['colores']: continue
        res = requests.post(f"{API_BASE}/admin/colores", json={
            "nombre": row["nombre"],
            "codigo_hex": row["codigo_hex"]
        }, headers=headers)
        if res.status_code == 201:
            new_color = res.json()
            id_maps['colores'][row["id"]] = new_color["id"]
            print(f"[OK] Color '{row['nombre']}'")
        else:
            print(f"[ERROR] Error color '{row['nombre']}': {res.text}")

    # -- 3. Categorias (Necesitamos orden correcto para padres)
    print("\n--- Migrando Categorías ---")
    c.execute("SELECT * FROM categorias")
    categorias = [dict(row) for row in c.fetchall()]
    cat_keys = categorias[0].keys() if categorias else []
    
    pendientes = list(categorias)
    max_iters = 10
    iter_count = 0
    while pendientes and iter_count < max_iters:
        iter_count += 1
        a_procesar = list(pendientes)
        for cat in a_procesar:
            if cat["id"] in id_maps['categorias']:
                pendientes.remove(cat)
                continue
                
            padre_old = cat.get("categoria_padre_id")
            padre_new = None
            if padre_old:
                if padre_old in id_maps['categorias']:
                    padre_new = id_maps['categorias'][padre_old]
                else:
                    continue
            
            payload = {
                "nombre": cat["nombre"],
                "descripcion": cat.get("descripcion", ""),
                "categoria_padre_id": padre_new,
                "activa": cat.get("activa", True)
            }
            if "orden" in cat_keys: payload["orden"] = cat.get("orden", 0)
            if "imagen" in cat_keys: payload["imagen"] = cat.get("imagen")
            if "slug" in cat_keys: payload["slug"] = cat.get("slug")

            res = requests.post(f"{API_BASE}/admin/categorias", json=payload, headers=headers)
            if res.status_code == 201:
                new_cat = res.json()
                id_maps['categorias'][cat["id"]] = new_cat["id"]
                pendientes.remove(cat)
                print(f"[OK] Categoría '{cat['nombre']}'")
            else:
                print(f"[ERROR] Error categoría '{cat['nombre']}': {res.text}")
                pendientes.remove(cat)

    # -- 4. Productos
    print("\n--- Migrando Productos ---")
    c.execute("SELECT * FROM productos")
    productos = [dict(row) for row in c.fetchall()]

    for row in productos:
        if row["id"] in id_maps['productos']: continue
        cat_new = id_maps['categorias'].get(row["categoria_id"])
        if not cat_new:
            print(f"[ERROR] Producto '{row['nombre']}': no se encontró nueva categoria")
            continue

        payload = {
            "nombre": row["nombre"],
            "descripcion": row.get("descripcion", ""),
            "categoria_id": cat_new,
            "precio_base": row.get("precio_base") or row.get("precio"),
            "precio_descuento": row.get("precio_descuento") or row.get("precio_oferta"),
            "activo": row.get("activo", True),
            "destacado": row.get("destacado", False),
            "color": row.get("color"),
            "color_hex": row.get("color_hex"),
            "dorsal": row.get("dorsal"),
            "numero": row.get("numero"),
            "version": row.get("version")
        }
        res = requests.post(f"{API_BASE}/admin/productos", json=payload, headers=headers)
        if res.status_code == 201:
            new_prod = res.json()
            id_maps['productos'][row["id"]] = new_prod["id"]
            print(f"[OK] Producto '{row['nombre']}'")
        else:
            print(f"[ERROR] Error producto '{row['nombre']}': {res.text}")

    print("\n--- Actualizando Productos Relacionados ---")
    for row in productos:
        rel_old = row.get("producto_relacionado_id")
        if rel_old and rel_old in id_maps['productos'] and row["id"] in id_maps['productos']:
            new_prod_id = id_maps['productos'][row["id"]]
            new_rel_id = id_maps['productos'][rel_old]
            res = requests.put(f"{API_BASE}/admin/productos/{new_prod_id}", json={
                "producto_relacionado_id": new_rel_id
            }, headers=headers)

    # -- 5. Stock
    print("\n--- Migrando Stock ---")
    c.execute("SELECT * FROM stock_talles")
    stock_rows = c.fetchall()
    
    count = 0
    for row in stock_rows:
        row_dict = dict(row)
        prod_new = id_maps['productos'].get(row_dict["producto_id"])
        talle_new = id_maps['talles'].get(row_dict["talle_id"])
        color_new = id_maps['colores'].get(row_dict.get("color_id")) if row_dict.get("color_id") else None

        if not prod_new or not talle_new:
            continue

        payload = {
            "producto_id": prod_new,
            "talle_id": talle_new,
            "cantidad": row_dict["cantidad"]
        }
        if color_new:
            payload["color_id"] = color_new

        res = requests.post(f"{API_BASE}/admin/stock", json=payload, headers=headers)
        if res.status_code == 200 or res.status_code == 201:
            count += 1
            if count % 50 == 0:
                print(f"[OK] {count} stock insertados...")
        else:
            print(f"[ERROR] Stock ProdID {prod_new}: {res.text}")

    print(f"[OK] Total stock insertados: {count}")

    # -- 6. Imágenes
    print("\n--- Migrando Imágenes ---")
    c.execute("SELECT * FROM imagenes_productos")
    img_rows = c.fetchall()
            
    img_count = 0
    for row in img_rows:
        row_dict = dict(row)
        prod_new = id_maps['productos'].get(row_dict["producto_id"])
        if not prod_new: continue

        img_url = row_dict["url"]
        if img_url.startswith('/static/uploads/'):
            filename = img_url.replace('/static/uploads/', '')
            local_filepath = os.path.join(LOCAL_UPLOADS, filename)
            
            if os.path.exists(local_filepath):
                with open(local_filepath, 'rb') as f:
                    file_bytes = f.read()
                
                files = {'imagen': (filename, file_bytes, 'image/webp')}
                data = {'es_principal': str(row_dict.get('es_principal', 'false')).lower()}
                
                auth_headers = {"Authorization": f"Bearer {token}"}
                res = requests.post(f"{API_BASE}/admin/productos/{prod_new}/imagenes", files=files, data=data, headers=auth_headers)
                if res.status_code == 201:
                    img_count += 1
                    if img_count % 10 == 0:
                        print(f"[OK] {img_count} imagenes subidas...")
                else:
                    print(f"[ERROR] {filename}: {res.text}")
            else:
                print(f"[ERROR] No encontrada: {local_filepath}")

    print(f"[OK] Total imagenes subidas: {img_count}")


    print("\n¡Migración vía API completada!")

if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        os.system("pip install requests -q")
        import requests
    migrate()
