import sys
import os
from flask import Flask
from dotenv import load_dotenv

# Ensure we are in the backend directory context
sys.path.append(os.getcwd())
load_dotenv()

from app import app
from models import TipoPromocion, db

with app.app_context():
    print(f"DATABASE_URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
    tipos = TipoPromocion.query.all()
    print(f"COUNT: {len(tipos)}")
    for t in tipos:
        print(f" - {t.id}: {t.nombre} ({t.descripcion})")
