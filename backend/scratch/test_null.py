import sys
import os
sys.path.append(os.getcwd())

from app import app
from models import db, PromocionProducto, TipoPromocion
from datetime import datetime

with app.app_context():
    print(f"Testing DB: {app.config['SQLALCHEMY_DATABASE_URI']}")
    try:
        # Create a test promotion with NULL fecha_fin
        tipo = TipoPromocion.query.first()
        if not tipo:
            tipo = TipoPromocion(nombre='test', descripcion='test')
            db.session.add(tipo)
            db.session.commit()
            
        test_promo = PromocionProducto(
            alcance='test',
            tipo_promocion_id=tipo.id,
            valor=0,
            activa=True,
            fecha_inicio=datetime.utcnow(),
            fecha_fin=None
        )
        db.session.add(test_promo)
        db.session.commit()
        print("✓ Successfully inserted a test promotion with NULL fecha_fin.")
        
        # Cleanup
        db.session.delete(test_promo)
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        print(f"✗ Failed to insert test promotion: {e}")
