from datetime import datetime, timedelta
from models import db, Pedido

def eliminar_pedidos_expirados(app):
    """
    Elimina pedidos pendientes que tienen más de 24 horas sin aprobación ni pago.
    """
    with app.app_context():
        try:
            # Pedidos con más de 24 horas
            limite = datetime.utcnow() - timedelta(hours=24)
            
            # Solo pedidos pendientes/registrados que no tengan comprobante ni externa_id
            pedidos = Pedido.query.filter(
                Pedido.estado == 'registrado',
                Pedido.fecha_creacion < limite,
                Pedido.external_id == None,
                Pedido.comprobante_url == None
            ).all()
            
            count = len(pedidos)
            for p in pedidos:
                # Opcional: devolver stock? (Si el stock se descontó al crear)
                db.session.delete(p)
            
            if count > 0:
                db.session.commit()
                print(f"DEBUG CLEANUP: Se eliminaron {count} pedidos expirados.")
        except Exception as e:
            print(f"ERROR CLEANUP: {str(e)}")
            db.session.rollback()
