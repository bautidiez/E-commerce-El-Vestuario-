from datetime import datetime
from sqlalchemy import or_
from .base import db

# Tabla de asociación para productos relacionados (Many-to-Many)
productos_relacionados = db.Table(
    'productos_relacionados',
    db.Column('producto_id', db.Integer, db.ForeignKey('productos.id'), primary_key=True),
    db.Column('relacionado_id', db.Integer, db.ForeignKey('productos.id'), primary_key=True)
)


class Categoria(db.Model):
    """Modelo para categorías de productos"""
    __tablename__ = 'categorias'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    imagen = db.Column(db.String(500), nullable=True)
    orden = db.Column(db.Integer, default=0)
    categoria_padre_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=True)
    activa = db.Column(db.Boolean, default=True)
    slug = db.Column(db.String(100), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    productos = db.relationship('Producto', backref='categoria', lazy=True)
    subcategorias = db.relationship(
        'Categoria',
        backref=db.backref('categoria_padre', remote_side=[id]),
        lazy=True,
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        db.Index('idx_categoria_padre', 'categoria_padre_id'),
        db.Index('idx_categoria_activa', 'activa'),
        db.Index('idx_categoria_orden', 'orden'),
    )

    def get_nivel(self):
        """Retorna el nivel jerárquico de la categoría (1, 2, o 3)"""
        if self.categoria_padre_id is None:
            return 1
        elif self.categoria_padre and self.categoria_padre.categoria_padre_id is None:
            return 2
        else:
            return 3

    def get_arbol_completo(self):
        result = self.to_dict()
        if self.subcategorias:
            result['subcategorias'] = [
                sub.get_arbol_completo()
                for sub in sorted(self.subcategorias, key=lambda x: x.nombre)
            ]
        return result

    def to_dict(self, include_subcategorias=False):
        data = {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'imagen': self.imagen,
            'orden': self.orden,
            'categoria_padre_id': self.categoria_padre_id,
            'activa': self.activa,
            'slug': self.slug,
            'nivel': self.get_nivel(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_subcategorias and self.subcategorias:
            data['subcategorias'] = [
                sub.to_dict(include_subcategorias=True)
                for sub in sorted(self.subcategorias, key=lambda x: x.nombre)
            ]
        return data


class Talle(db.Model):
    """Modelo para talles"""
    __tablename__ = 'talles'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(10), nullable=False, unique=True)
    orden = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {'id': self.id, 'nombre': self.nombre, 'orden': self.orden}


class Color(db.Model):
    """Modelo para colores de productos"""
    __tablename__ = 'colores'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    codigo_hex = db.Column(db.String(7), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'codigo_hex': self.codigo_hex,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class StockTalle(db.Model):
    """Modelo para stock por color, talle de cada producto"""
    __tablename__ = 'stock_talles'

    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    color_id = db.Column(db.Integer, db.ForeignKey('colores.id'), nullable=True)
    talle_id = db.Column(db.Integer, db.ForeignKey('talles.id'), nullable=False)
    cantidad = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    talle = db.relationship('Talle', backref='stock_talles', lazy='joined')
    color = db.relationship('Color', backref='stock_talles', lazy='joined')

    __table_args__ = (
        db.UniqueConstraint('producto_id', 'color_id', 'talle_id', name='_producto_color_talle_uc'),
        db.Index('idx_stock_producto', 'producto_id'),
        db.Index('idx_stock_talle', 'talle_id'),
        db.Index('idx_stock_cantidad', 'cantidad'),
        db.Index('idx_stock_producto_cantidad', 'producto_id', 'cantidad'),
    )

    def tiene_stock(self):
        return self.cantidad >= 4

    def reducir_stock(self, cantidad=1):
        if self.cantidad >= cantidad:
            self.cantidad -= cantidad
            return True
        return False

    def aumentar_stock(self, cantidad=1):
        self.cantidad += cantidad

    def to_dict(self):
        return {
            'id': self.id,
            'producto_id': self.producto_id,
            'producto_nombre': self.producto.nombre if self.producto else None,
            'color_id': self.color_id,
            'color_nombre': self.color.nombre if self.color else None,
            'talle_id': self.talle_id,
            'talle_nombre': self.talle.nombre if self.talle else None,
            'cantidad': self.cantidad,
            'tiene_stock': self.tiene_stock(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ImagenProducto(db.Model):
    """Modelo para imágenes de productos"""
    __tablename__ = 'imagenes_productos'

    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    es_principal = db.Column(db.Boolean, default=False)
    orden = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'producto_id': self.producto_id,
            'url': self.url,
            'es_principal': self.es_principal,
            'orden': self.orden
        }


class Producto(db.Model):
    """Modelo para productos"""
    __tablename__ = 'productos'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    precio_base = db.Column(db.Float, nullable=False)
    precio_descuento = db.Column(db.Float, nullable=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    destacado = db.Column(db.Boolean, default=False)
    color = db.Column(db.String(100), nullable=True)
    color_hex = db.Column(db.String(7), nullable=True)
    dorsal = db.Column(db.String(100), nullable=True)
    numero = db.Column(db.Integer, nullable=True)
    version = db.Column(db.String(50), nullable=True)
    producto_relacionado_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=True)
    ventas_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    imagenes = db.relationship('ImagenProducto', backref='producto', lazy='selectin', cascade='all, delete-orphan')
    stock_talles = db.relationship('StockTalle', backref='producto', lazy='selectin', cascade='all, delete-orphan')

    relacionados = db.relationship(
        'Producto',
        secondary=productos_relacionados,
        primaryjoin=id == productos_relacionados.c.producto_id,
        secondaryjoin=id == productos_relacionados.c.relacionado_id,
        backref=db.backref('relacionados_inversos', lazy='dynamic'),
        lazy='selectin'
    )

    __table_args__ = (
        db.Index('idx_producto_categoria', 'categoria_id'),
        db.Index('idx_producto_activo', 'activo'),
        db.Index('idx_producto_destacado_activo', 'destacado', 'activo'),
    )

    def get_precio_actual(self):
        return self.precio_descuento if self.precio_descuento else self.precio_base

    def tiene_stock(self):
        return any(st.cantidad >= 4 for st in self.stock_talles)

    def tiene_stock_bajo(self):
        return any(0 < st.cantidad <= 3 for st in self.stock_talles)

    def esta_agotado(self):
        if not self.stock_talles:
            return True
        return all(st.cantidad <= 0 for st in self.stock_talles)

    def get_promociones_activas(self):
        from .promociones import PromocionProducto
        ahora = datetime.utcnow()
        promociones = [p for p in self.promociones if p.esta_activa()]
        promociones_cat = PromocionProducto.query.filter(
            PromocionProducto.activa == True,
            PromocionProducto.fecha_inicio <= ahora,
            or_(PromocionProducto.fecha_fin >= ahora, PromocionProducto.fecha_fin == None),
            PromocionProducto.categorias.any(id=self.categoria_id)
        ).all()
        promociones_global = PromocionProducto.query.filter(
            PromocionProducto.alcance == 'tienda',
            PromocionProducto.activa == True,
            PromocionProducto.fecha_inicio <= ahora,
            or_(PromocionProducto.fecha_fin >= ahora, PromocionProducto.fecha_fin == None)
        ).all()
        todas = {p.id: p for p in (promociones + promociones_cat + promociones_global)}
        return list(todas.values())

    def to_dict(self, include_stock=True):
        data = {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'precio_base': self.precio_base,
            'precio_descuento': self.precio_descuento,
            'precio_actual': self.get_precio_actual(),
            'categoria_id': self.categoria_id,
            'categoria_nombre': self.categoria.nombre if self.categoria else None,
            'categoria_principal': (
                self.categoria.categoria_padre.nombre
                if (self.categoria and self.categoria.categoria_padre)
                else (self.categoria.nombre if self.categoria else None)
            ),
            'subcategoria': (
                self.categoria.nombre
                if (self.categoria and self.categoria.categoria_padre)
                else '-'
            ),
            'activo': self.activo,
            'destacado': self.destacado,
            'color': self.color,
            'color_hex': self.color_hex,
            'dorsal': self.dorsal,
            'numero': self.numero,
            'version': self.version,
            'producto_relacionado_id': self.producto_relacionado_id,
            'ventas_count': self.ventas_count,
            'tiene_stock': self.tiene_stock(),
            'tiene_stock_bajo': self.tiene_stock_bajo(),
            'esta_agotado': self.esta_agotado(),
            'imagenes': [img.to_dict() for img in sorted(self.imagenes, key=lambda x: x.orden or 0)],
            'promociones': [p.to_dict() for p in self.get_promociones_activas()],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_stock:
            data['stock_talles'] = [
                st.to_dict() for st in self.stock_talles
                if st.talle and st.talle.nombre != 'XS'
            ]
            data['relacionados'] = [
                {'id': rel.id, 'nombre': rel.nombre, 'color': rel.color, 'color_hex': rel.color_hex, 'slug': rel.id}
                for rel in self.relacionados
            ]
        return data
