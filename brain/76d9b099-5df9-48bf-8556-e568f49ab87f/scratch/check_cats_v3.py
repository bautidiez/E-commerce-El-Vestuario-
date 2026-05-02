
import os
import sys
# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app import app
from models import db, Categoria

with app.app_context():
    cats = Categoria.query.all()
    print(f"Total categories: {len(cats)}")
    # Print sorted by parent and name to see duplicates
    sorted_cats = sorted(cats, key=lambda x: (x.categoria_padre_id or 0, x.nombre))
    for c in sorted_cats:
        print(f"ID: {c.id}, Name: '{c.nombre}', Parent: {c.categoria_padre_id}")
