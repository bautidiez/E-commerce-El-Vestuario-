
import os
import json
from models.base import db
from models.catalogo import Producto, Categoria, StockTalle, ImagenProducto
from models.promociones import PromocionProducto

def backup_data():
    from app import app
    with app.app_context():
        # Exportar productos
        productos = Producto.query.all()
        data = []
        for p in productos:
            prod_data = p.to_dict(include_stock=True)
            data.append(prod_data)
        
        backup_path = os.path.join(os.getcwd(), 'backup_productos.json')
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        print(f"Backup creado exitosamente en {backup_path}")
        print(f"Total productos respaldados: {len(productos)}")

if __name__ == "__main__":
    backup_data()
