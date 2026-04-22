import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app import app
from models import db, Pedido, VentaExterna

with app.app_context():
    print(f"Total Pedidos: {Pedido.query.count()}")
    print(f"Total VentaExterna: {VentaExterna.query.count()}")
    
    last_p = Pedido.query.order_by(Pedido.created_at.desc()).first()
    if last_p:
        print(f"Last Pedido: ID={last_p.id}, Num={last_p.numero_pedido}, Date={last_p.created_at}, Total={last_p.total}")
    
    last_v = VentaExterna.query.order_by(VentaExterna.fecha.desc()).first()
    if last_v:
        print(f"Last VentaExterna: ID={last_v.id}, Date={last_v.fecha}, Total={last_v.ganancia_total}")
