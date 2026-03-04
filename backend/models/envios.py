from datetime import datetime
from .base import db


class Shipment(db.Model):
    """Modelo para envíos y tracking"""
    __tablename__ = 'shipments'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    transportista = db.Column(db.String(100), nullable=False)
    numero_guia = db.Column(db.String(100))
    estado = db.Column(db.String(50), default='preparando')
    costo = db.Column(db.Float)
    tiempo_estimado = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    updates = db.relationship('TrackingUpdate', backref='shipment', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'transportista': self.transportista,
            'numero_guia': self.numero_guia,
            'estado': self.estado,
            'costo': self.costo,
            'tiempo_estimado': self.tiempo_estimado,
            'updates': [u.to_dict() for u in self.updates],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TrackingUpdate(db.Model):
    """Modelo para historial de seguimiento"""
    __tablename__ = 'tracking_updates'

    id = db.Column(db.Integer, primary_key=True)
    shipment_id = db.Column(db.Integer, db.ForeignKey('shipments.id'), nullable=False)
    estado = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'estado': self.estado,
            'descripcion': self.descripcion,
            'fecha': self.fecha.isoformat() if self.fecha else None
        }
