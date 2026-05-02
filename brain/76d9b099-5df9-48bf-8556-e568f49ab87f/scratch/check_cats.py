
import os
import sys
# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app import create_app
from extensions import db
from models import Categoria

app = create_app()
with app.app_context():
    cats = Categoria.query.all()
    print(f"Total categories: {len(cats)}")
    for c in cats:
        print(f"ID: {c.id}, Name: '{c.nombre}', Parent: {c.categoria_padre_id}")
