from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from .base import db


class Cliente(db.Model):
    """Modelo para clientes registrados"""
    __tablename__ = 'clientes'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    telefono = db.Column(db.String(50))
    telefono_verificado = db.Column(db.Boolean, default=False)
    metodo_verificacion = db.Column(db.String(20), default='telefono')
    codigo_verificacion = db.Column(db.String(6), nullable=True)
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    imagen_url = db.Column(db.String(500), nullable=True)
    acepta_newsletter = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_cliente_email', 'email', unique=True),
        db.Index('idx_cliente_google', 'google_id', unique=True),
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'email': self.email,
            'telefono': self.telefono,
            'metodo_verificacion': self.metodo_verificacion,
            'acepta_newsletter': self.acepta_newsletter,
            'imagen_url': self.imagen_url,
            'google_logged': bool(self.google_id),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Favorito(db.Model):
    """Modelo para productos favoritos de clientes"""
    __tablename__ = 'favoritos'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.relationship('Cliente', backref=db.backref('favoritos', lazy='dynamic'))
    producto = db.relationship('Producto')

    __table_args__ = (
        db.UniqueConstraint('cliente_id', 'producto_id', name='_cliente_producto_favorito_uc'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'cliente_id': self.cliente_id,
            'producto_id': self.producto_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Carrito(db.Model):
    """Modelo para carrito de compras persistente"""
    __tablename__ = 'carritos'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False, unique=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cliente = db.relationship('Cliente', backref=db.backref('carrito', uselist=False))
    items = db.relationship('ItemCarrito', backref='carrito', lazy='joined', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'cliente_id': self.cliente_id,
            'items': [item.to_dict() for item in self.items],
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ItemCarrito(db.Model):
    """Items dentro del carrito persistente"""
    __tablename__ = 'items_carrito'

    id = db.Column(db.Integer, primary_key=True)
    carrito_id = db.Column(db.Integer, db.ForeignKey('carritos.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    talle_id = db.Column(db.Integer, db.ForeignKey('talles.id'), nullable=False)
    cantidad = db.Column(db.Integer, default=1)

    producto = db.relationship('Producto')
    talle = db.relationship('Talle')

    def to_dict(self):
        return {
            'producto_id': self.producto_id,
            'producto': self.producto.to_dict(include_stock=False) if self.producto else None,
            'talle_id': self.talle_id,
            'talle': self.talle.to_dict() if self.talle else None,
            'cantidad': self.cantidad
        }
