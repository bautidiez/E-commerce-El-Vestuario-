from datetime import datetime
from .base import db


class MetodoPago(db.Model):
    """Modelo para métodos de pago"""
    __tablename__ = 'metodos_pago'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {'id': self.id, 'nombre': self.nombre, 'descripcion': self.descripcion, 'activo': self.activo}


class Pedido(db.Model):
    """Modelo para pedidos"""
    __tablename__ = 'pedidos'

    id = db.Column(db.Integer, primary_key=True)
    numero_pedido = db.Column(db.String(50), unique=True, nullable=False)
    cliente_nombre = db.Column(db.String(200), nullable=False)
    cliente_email = db.Column(db.String(200), nullable=False)
    cliente_telefono = db.Column(db.String(50))
    cliente_direccion = db.Column(db.Text, nullable=False)
    cliente_codigo_postal = db.Column(db.String(20), nullable=False)
    cliente_localidad = db.Column(db.String(200), nullable=False)
    cliente_provincia = db.Column(db.String(200), nullable=False)
    cliente_dni = db.Column(db.String(20))

    metodo_pago_id = db.Column(db.Integer, db.ForeignKey('metodos_pago.id'), nullable=False)
    metodo_envio = db.Column(db.String(100))

    subtotal = db.Column(db.Float, nullable=False)
    descuento = db.Column(db.Float, default=0)
    costo_envio = db.Column(db.Float, default=0)
    total = db.Column(db.Float, nullable=False)

    estado = db.Column(db.String(50), default='pendiente_aprobacion')
    notas = db.Column(db.Text)

    aprobado = db.Column(db.Boolean, default=False, nullable=False)
    fecha_expiracion = db.Column(db.DateTime, nullable=True)
    fecha_aprobacion = db.Column(db.DateTime, nullable=True)
    admin_aprobador_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)

    external_id = db.Column(db.String(100))
    comprobante_url = db.Column(db.String(500))
    codigo_pago_unico = db.Column(db.String(50))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_pedido_estado', 'estado'),
        db.Index('idx_pedido_created_at', 'created_at'),
        db.Index('idx_pedido_numero', 'numero_pedido', unique=True),
        db.Index('idx_pedido_aprobado', 'aprobado'),
        db.Index('idx_pedido_estado_aprobado', 'estado', 'aprobado'),
    )

    metodo_pago = db.relationship('MetodoPago', backref='pedidos')
    items = db.relationship('ItemPedido', backref='pedido', lazy=True, cascade='all, delete-orphan')
    envio = db.relationship('Shipment', backref='pedido', uselist=False, cascade='all, delete-orphan')
    admin_aprobador = db.relationship('Admin', foreign_keys=[admin_aprobador_id], backref='pedidos_aprobados')

    def to_dict(self):
        return {
            'id': self.id,
            'numero_pedido': self.numero_pedido,
            'cliente_nombre': self.cliente_nombre,
            'cliente_email': self.cliente_email,
            'cliente_telefono': self.cliente_telefono,
            'cliente_direccion': self.cliente_direccion,
            'cliente_codigo_postal': self.cliente_codigo_postal,
            'cliente_localidad': self.cliente_localidad,
            'cliente_provincia': self.cliente_provincia,
            'cliente_dni': self.cliente_dni,
            'metodo_pago_id': self.metodo_pago_id,
            'metodo_pago_nombre': self.metodo_pago.nombre if self.metodo_pago else None,
            'metodo_envio': self.metodo_envio,
            'subtotal': self.subtotal,
            'descuento': self.descuento,
            'costo_envio': self.costo_envio,
            'total': self.total,
            'estado': self.estado,
            'notas': self.notas,
            'aprobado': self.aprobado,
            'fecha_expiracion': self.fecha_expiracion.isoformat() if self.fecha_expiracion else None,
            'fecha_aprobacion': self.fecha_aprobacion.isoformat() if self.fecha_aprobacion else None,
            'admin_aprobador_id': self.admin_aprobador_id,
            'admin_aprobador_username': self.admin_aprobador.username if self.admin_aprobador else None,
            'external_id': self.external_id,
            'comprobante_url': self.comprobante_url,
            'codigo_pago_unico': self.codigo_pago_unico,
            'items': [item.to_dict() for item in self.items],
            'envio': self.envio.to_dict() if self.envio else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ItemPedido(db.Model):
    """Modelo para items de pedidos"""
    __tablename__ = 'items_pedido'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    talle_id = db.Column(db.Integer, db.ForeignKey('talles.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    descuento_aplicado = db.Column(db.Float, default=0)
    subtotal = db.Column(db.Float, nullable=False)

    producto = db.relationship('Producto', backref='items_pedido')
    talle = db.relationship('Talle', backref='items_pedido')

    def to_dict(self):
        return {
            'id': self.id,
            'pedido_id': self.pedido_id,
            'producto_id': self.producto_id,
            'producto_nombre': self.producto.nombre if self.producto else None,
            'talle_id': self.talle_id,
            'talle_nombre': self.talle.nombre if self.talle else None,
            'cantidad': self.cantidad,
            'precio_unitario': self.precio_unitario,
            'descuento_aplicado': self.descuento_aplicado,
            'subtotal': self.subtotal
        }


class NotaPedido(db.Model):
    """Modelo para notas internas de pedidos (solo admin)"""
    __tablename__ = 'notas_pedido'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    pedido = db.relationship('Pedido', backref='notas_internas')
    admin = db.relationship('Admin', backref='notas_pedido')

    def to_dict(self):
        return {
            'id': self.id,
            'pedido_id': self.pedido_id,
            'admin_id': self.admin_id,
            'admin_username': self.admin.username if self.admin else None,
            'contenido': self.contenido,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
