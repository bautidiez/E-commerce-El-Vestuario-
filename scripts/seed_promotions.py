import sys
import os

# Añadir el directorio backend al path para poder importar los modelos
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from flask import Flask
from models import TipoPromocion, db
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def seed_promotions():
    with app.app_context():
        # Lista de tipos de promoción a crear
        tipos = [
            {'nombre': 'descuento_porcentaje', 'descripcion': 'Descuento por porcentaje (ej: 10%)'},
            {'nombre': 'descuento_fijo', 'descripcion': 'Descuento de monto fijo (ej: $500)'},
            {'nombre': '2x1', 'descripcion': 'Llevas 2 pagas 1'},
            {'nombre': '3x2', 'descripcion': 'Llevas 3 pagas 2'}
        ]
        
        for tipo_data in tipos:
            # Verificar si ya existe
            existente = TipoPromocion.query.filter_by(nombre=tipo_data['nombre']).first()
            if not existente:
                nuevo_tipo = TipoPromocion(
                    nombre=tipo_data['nombre'],
                    descripcion=tipo_data['descripcion']
                )
                db.session.add(nuevo_tipo)
                print(f"Creado tipo de promoción: {tipo_data['nombre']}")
            else:
                print(f"El tipo de promoción '{tipo_data['nombre']}' ya existe.")
        
        try:
            db.session.commit()
            print("Sincronización de tipos de promoción completada con éxito.")
        except Exception as e:
            db.session.rollback()
            print(f"Error al sincronizar tipos de promoción: {e}")

if __name__ == '__main__':
    seed_promotions()
