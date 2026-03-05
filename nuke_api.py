import requests

API_BASE = "https://elvestuario-backend.onrender.com/api"

# Login to get JWT
res = requests.post(f"{API_BASE}/auth/login", json={
    "username": "admin",
    "password": "ElVestuario2024!Admin"
})
token = res.json().get('access_token')
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

print("Borrando Productos...")
# Fetch all products
prods = requests.get(f"{API_BASE}/productos?page=1&page_size=1000").json().get('items', [])
for p in prods:
    # Set it inactive first or try to delete
    res = requests.delete(f"{API_BASE}/admin/productos/{p['id']}", headers=headers)
    if res.status_code == 200:
        print(f"Borrando Prod {p['id']} - {p['nombre']}")
    else:
        print(f"Error borrando prod {p['id']}: {res.text}")

print("\nBorrando Categorias...")
cats = requests.get(f"{API_BASE}/categorias").json()
# Flatten categories
all_cats = []
def flatten(c_list):
    for c in c_list:
        all_cats.append(c)
        if c.get("subcategorias"):
            flatten(c["subcategorias"])
flatten(cats)

# Sort by id descending so we delete children first
all_cats.sort(key=lambda x: x["id"], reverse=True)
for c in all_cats:
    res = requests.delete(f"{API_BASE}/admin/categorias/{c['id']}", headers=headers)
    if res.status_code == 200:
        print(f"Borrando Cat {c['id']} - {c['nombre']}")
    else:
        print(f"Error borrando cat {c['id']}: {res.text}")

print("Limpieza terminada.")
