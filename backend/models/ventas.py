from datetime import datetime
from .base import db


class VentaExterna(db.Model):
    """Modelo para ventas realizadas fuera de la tienda web"""
    __tablename__ = 'ventas_externas'

    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    talle_id = db.Column(db.Integer, db.ForeignKey('talles.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    ganancia_total = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    notas = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    producto = db.relationship('Producto', backref='ventas_externas')
    talle = db.relationship('Talle', backref='ventas_externas')
    admin = db.relationship('Admin', backref='ventas_externas')

    __table_args__ = (
        db.Index('idx_venta_externa_producto', 'producto_id'),
        db.Index('idx_venta_externa_fecha', 'fecha'),
        db.Index('idx_venta_externa_admin', 'admin_id'),
        db.Index('idx_venta_externa_fecha_producto', 'fecha', 'producto_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'producto_id': self.producto_id,
            'producto_nombre': self.producto.nombre if self.producto else None,
            'talle_id': self.talle_id,
            'talle_nombre': self.talle.nombre if self.talle else None,
            'cantidad': self.cantidad,
            'precio_unitario': self.precio_unitario,
            'ganancia_total': self.ganancia_total,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'admin_id': self.admin_id,
            'admin_username': self.admin.username if self.admin else None,
            'notas': self.notas,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
