from datetime import datetime
from .base import db

# Tablas de vinculación para promociones
promocion_productos_link = db.Table(
    'promocion_productos_link',
    db.Column('promocion_id', db.Integer, db.ForeignKey('promociones_productos.id'), primary_key=True),
    db.Column('producto_id', db.Integer, db.ForeignKey('productos.id'), primary_key=True)
)

promocion_categorias_link = db.Table(
    'promocion_categorias_link',
    db.Column('promocion_id', db.Integer, db.ForeignKey('promociones_productos.id'), primary_key=True),
    db.Column('categoria_id', db.Integer, db.ForeignKey('categorias.id'), primary_key=True)
)


class TipoPromocion(db.Model):
    """Modelo para tipos de promoción"""
    __tablename__ = 'tipos_promocion'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)  # '2x1', '3x2', 'descuento_porcentaje', 'descuento_fijo'
    descripcion = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion
        }


class PromocionProducto(db.Model):
    """Modelo para promociones de productos"""
    __tablename__ = 'promociones_productos'

    id = db.Column(db.Integer, primary_key=True)
    alcance = db.Column(db.String(20), default='producto')  # 'producto', 'categoria', 'tienda'
    tipo_promocion_id = db.Column(db.Integer, db.ForeignKey('tipos_promocion.id'), nullable=False)
    valor = db.Column(db.Float)
    es_cupon = db.Column(db.Boolean, default=False)
    codigo = db.Column(db.String(50), unique=True, nullable=True)
    envio_gratis = db.Column(db.Boolean, default=False)
    activa = db.Column(db.Boolean, default=True)
    fecha_inicio = db.Column(db.DateTime, nullable=False)
    fecha_fin = db.Column(db.DateTime, nullable=True) # None para indefinida
    compra_minima = db.Column(db.Float, default=0.0)
    max_usos = db.Column(db.Integer, nullable=True)
    usos_actuales = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tipo_promocion = db.relationship('TipoPromocion', backref='promociones')
    productos = db.relationship('Producto', secondary=promocion_productos_link, backref='promociones')
    categorias = db.relationship('Categoria', secondary=promocion_categorias_link, backref='promociones')

    def esta_activa(self):
        ahora = datetime.utcnow()
        if not self.activa:
            return False
        if self.fecha_inicio > ahora:
            return False
        # Si fecha_fin es None, es indefinida
        if self.fecha_fin is None:
            return True
        return ahora <= self.fecha_fin

    def calcular_descuento(self, cantidad, precio_unitario):
        if not self.esta_activa():
            return 0
        tipo = self.tipo_promocion.nombre
        if tipo == 'descuento_porcentaje':
            return (precio_unitario * cantidad * self.valor) / 100
        elif tipo == 'descuento_fijo':
            return self.valor * cantidad
        elif tipo == '2x1':
            return precio_unitario * (cantidad // 2)
        elif tipo == '3x2':
            return precio_unitario * (cantidad // 3)
        elif tipo.startswith('llevas_'):
            partes = tipo.split('_')
            if len(partes) >= 4:
                lleva = int(partes[1])
                paga = int(partes[3])
                return precio_unitario * ((cantidad // lleva) * (lleva - paga))
        return 0

    def _format_datetime(self, dt):
        if not dt:
            return None
        iso = dt.isoformat()
        if not dt.tzinfo and not iso.endswith('Z') and '+' not in iso:
            return iso + 'Z'
        return iso

    def to_dict(self):
        return {
            'id': self.id,
            'alcance': self.alcance,
            'tipo_promocion_id': self.tipo_promocion_id,
            'tipo_promocion_nombre': self.tipo_promocion.nombre if self.tipo_promocion else None,
            'valor': self.valor,
            'activa': self.activa,
            'esta_activa': self.esta_activa(),
            'fecha_inicio': self._format_datetime(self.fecha_inicio),
            'fecha_fin': self._format_datetime(self.fecha_fin),
            'productos_ids': [p.id for p in self.productos],
            'productos_nombres': [p.nombre for p in self.productos],
            'categorias_ids': [c.id for c in self.categorias],
            'categorias_nombres': [c.nombre for c in self.categorias],
            'es_cupon': self.es_cupon,
            'codigo': self.codigo,
            'envio_gratis': self.envio_gratis,
            'compra_minima': self.compra_minima,
            'max_usos': self.max_usos,
            'usos_actuales': self.usos_actuales
        }
