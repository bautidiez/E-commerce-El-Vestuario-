import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from flask import Flask
from models import TipoPromocion, db
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
db.init_app(app)

with app.app_context():
    tipos = TipoPromocion.query.all()
    print("\n--- TIPOS DE PROMOCIÓN REGISTRADOS ---")
    for t in tipos:
        print(f"ID: {t.id} | Nombre: {t.nombre}")
    print("--------------------------------------\n")
