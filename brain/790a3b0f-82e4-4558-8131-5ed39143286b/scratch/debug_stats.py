import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app import app
from models import db, Pedido, VentaExterna
from datetime import datetime, timedelta

with app.app_context():
    print("--- PEDIDOS (21/04 - 22/04) ---")
    pedidos = Pedido.query.filter(Pedido.created_at >= '2026-04-20').all()
    for p in pedidos:
        print(f"ID: {p.id}, Num: {p.numero_pedido}, Total: {p.total}, Status: {p.estado}, Aprobado: {p.aprobado}, Fecha: {p.created_at}")

    print("\n--- VENTAS EXTERNAS (21/04 - 22/04) ---")
    ventas = VentaExterna.query.filter(VentaExterna.fecha >= '2026-04-20').all()
    for v in ventas:
        print(f"ID: {v.id}, Producto: {v.producto_nombre}, Total: {v.ganancia_total}, Fecha: {v.fecha}, Creado: {v.created_at}")

    # Check for anything on the 22nd
    print("\n--- DATA ON 22/04 ---")
    d22_start = datetime(2026, 4, 22, 0, 0, 0)
    d22_end = datetime(2026, 4, 22, 23, 59, 59)
    
    v22 = VentaExterna.query.filter(VentaExterna.fecha.between(d22_start, d22_end)).all()
    for v in v22:
        print(f"Venta Ext 22/04: {v.id}, Total: {v.ganancia_total}, Fecha: {v.fecha}")
        
    p22 = Pedido.query.filter(Pedido.created_at.between(d22_start, d22_end)).all()
    for p in p22:
        print(f"Pedido 22/04: {p.id}, Total: {p.total}, Fecha: {p.created_at}")
