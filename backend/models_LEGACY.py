from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# db se inicializarÃ¡ en app.py
db = SQLAlchemy()

class Admin(db.Model):
    """Modelo para administradores"""
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Índices explícitos
    __table_args__ = (
        db.Index('idx_admin_username', 'username', unique=True),
    )
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Categoria(db.Model):
    """Modelo para categorías de productos"""
    __tablename__ = 'categorias'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    imagen = db.Column(db.String(500), nullable=True)  # URL de imagen opcional
    orden = db.Column(db.Integer, default=0)  # Para ordenamiento personalizado
    categoria_padre_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=True)
    activa = db.Column(db.Boolean, default=True)
    slug = db.Column(db.String(100), unique=True, nullable=True) # URL friendly version of name
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    productos = db.relationship('Producto', backref='categoria', lazy=True)
    subcategorias = db.relationship('Categoria', backref=db.backref('categoria_padre', remote_side=[id]), lazy=True, cascade='all, delete-orphan')
    
    # Índices para mejorar rendimiento de consultas jerárquicas
    __table_args__ = (
        db.Index('idx_categoria_padre', 'categoria_padre_id'),
        db.Index('idx_categoria_activa', 'activa'),
        db.Index('idx_categoria_orden', 'orden'),
    )
    
    def get_nivel(self):
        """Retorna el nivel jerárquico de la categoría (1, 2, o 3)"""
        if self.categoria_padre_id is None:
            return 1  # Categoría padre
        elif self.categoria_padre and self.categoria_padre.categoria_padre_id is None:
            return 2  # Subcategoría
        else:
            return 3  # Sub-subcategoría
    
    def get_arbol_completo(self):
        """Retorna la estructura jerárquica completa de esta categoría"""
        result = self.to_dict()
        if self.subcategorias:
            result['subcategorias'] = [sub.get_arbol_completo() for sub in sorted(self.subcategorias, key=lambda x: x.nombre)]
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
            data['subcategorias'] = [sub.to_dict(include_subcategorias=True) for sub in sorted(self.subcategorias, key=lambda x: x.nombre)]
        return data



# Tabla de asociación para productos relacionados (Many-to-Many)
productos_relacionados = db.Table('productos_relacionados',
    db.Column('producto_id', db.Integer, db.ForeignKey('productos.id'), primary_key=True),
    db.Column('relacionado_id', db.Integer, db.ForeignKey('productos.id'), primary_key=True)
)

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
    color = db.Column(db.String(100), nullable=True)  # Ej: "Negro Y Plata", "Rojo Y Plata"
    color_hex = db.Column(db.String(7), nullable=True)  # CÃ³digo hexadecimal del color
    dorsal = db.Column(db.String(100), nullable=True)  # Ej: "10 - Messi", "10 - Neymar"
    numero = db.Column(db.Integer, nullable=True)  # Ej: 5, 7, 8, 10, 11
    version = db.Column(db.String(50), nullable=True)  # Ej: "Hincha", "Jugador"
    producto_relacionado_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=True)  # Producto relacionado (mismo diseÃ±o, diferente color)
    ventas_count = db.Column(db.Integer, default=0)  # Contador de ventas para ordenamiento
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Usar 'selectin' para cargar relaciones de forma eficiente (reduce N+1 queries)
    imagenes = db.relationship('ImagenProducto', backref='producto', lazy='selectin', cascade='all, delete-orphan')
    stock_talles = db.relationship('StockTalle', backref='producto', lazy='selectin', cascade='all, delete-orphan')
    
    # RELACIÓN N:M para productos relacionados
    relacionados = db.relationship(
        'Producto',
        secondary=productos_relacionados,
        primaryjoin=id==productos_relacionados.c.producto_id,
        secondaryjoin=id==productos_relacionados.c.relacionado_id,
        backref=db.backref('relacionados_inversos', lazy='dynamic'),
        lazy='selectin'
    )

    # Relación Many-to-Many con promociones (definida en PromocionProducto)
    
    # Índices para mejorar rendimiento de consultas
    __table_args__ = (
        db.Index('idx_producto_categoria', 'categoria_id'),
        db.Index('idx_producto_activo', 'activo'),
        db.Index('idx_producto_destacado_activo', 'destacado', 'activo'),
    )
    
    def get_precio_actual(self):
        """Retorna el precio actual (con descuento si existe)"""
        return self.precio_descuento if self.precio_descuento else self.precio_base
    
    def tiene_stock(self):
        """Verifica si el producto tiene stock disponible (>= 4)"""
        return any(st.cantidad >= 4 for st in self.stock_talles)

    def tiene_stock_bajo(self):
        """Verifica si el producto tiene stock bajo (entre 1 y 3)"""
        return any(0 < st.cantidad <= 3 for st in self.stock_talles)

    def esta_agotado(self):
        """Verifica si el producto está agotado (stock <= 0 en todos los talles)"""
        if not self.stock_talles:
            return True
        return all(st.cantidad <= 0 for st in self.stock_talles)
    
    def get_promociones_activas(self):
        """Retorna las promociones activas para este producto"""
        from datetime import datetime
        ahora = datetime.utcnow()
        
        # Promociones directas, por categoría o globales
        promociones = [p for p in self.promociones if p.esta_activa()]
        
        # También buscar promociones por categoría
        promociones_cat = PromocionProducto.query.filter(
            PromocionProducto.activa == True,
            PromocionProducto.fecha_inicio <= ahora,
            PromocionProducto.fecha_fin >= ahora,
            PromocionProducto.categorias.any(id=self.categoria_id)
        ).all()
        
        # También buscar promociones globales
        promociones_global = PromocionProducto.query.filter(
            PromocionProducto.alcance == 'tienda',
            PromocionProducto.activa == True,
            PromocionProducto.fecha_inicio <= ahora,
            PromocionProducto.fecha_fin >= ahora
        ).all()
        
        # Combinar y evitar duplicados
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
            # Lógica para columnas de tabla
            'categoria_principal': self.categoria.categoria_padre.nombre if (self.categoria and self.categoria.categoria_padre) else (self.categoria.nombre if self.categoria else None),
            'subcategoria': self.categoria.nombre if (self.categoria and self.categoria.categoria_padre) else "-",
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
            'imagenes': [img.to_dict() for img in self.imagenes],
            'promociones': [p.to_dict() for p in self.get_promociones_activas()],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_stock:
            data['stock_talles'] = [st.to_dict() for st in self.stock_talles if st.talle and st.talle.nombre != 'XS']
            
            # Incluir productos relacionados para selector de colores
            # Evitar recursividad infinita enviando info mínima
            data['relacionados'] = []
            for rel in self.relacionados:
                data['relacionados'].append({
                    'id': rel.id,
                    'nombre': rel.nombre,
                    'color': rel.color,
                    'color_hex': rel.color_hex,
                    'slug': rel.id # Usar ID por ahora
                })
        return data

class Talle(db.Model):
    """Modelo para talles"""
    __tablename__ = 'talles'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(10), nullable=False, unique=True)  # S, M, L, XL, etc.
    orden = db.Column(db.Integer, default=0)  # Para ordenar los talles
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'orden': self.orden
        }

class Color(db.Model):
    """Modelo para colores de productos"""
    __tablename__ = 'colores'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)  # "Negro Y Plata", "Rojo Y Plata", etc.
    codigo_hex = db.Column(db.String(7), nullable=True)  # Opcional: cÃ³digo hexadecimal del color
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
    color_id = db.Column(db.Integer, db.ForeignKey('colores.id'), nullable=True)  # NULL para productos sin color especÃ­fico
    talle_id = db.Column(db.Integer, db.ForeignKey('talles.id'), nullable=False)
    cantidad = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Usar 'joined' para relaciones simples (talle y color)
    talle = db.relationship('Talle', backref='stock_talles', lazy='joined')
    color = db.relationship('Color', backref='stock_talles', lazy='joined')
    
    # Índices para optimizar consultas de stock
    __table_args__ = (
        db.UniqueConstraint('producto_id', 'color_id', 'talle_id', name='_producto_color_talle_uc'),
        db.Index('idx_stock_producto', 'producto_id'),
        db.Index('idx_stock_talle', 'talle_id'),
        db.Index('idx_stock_cantidad', 'cantidad'),
        db.Index('idx_stock_producto_cantidad', 'producto_id', 'cantidad'),  # Índice compuesto
    )
    
    def tiene_stock(self):
        """Stock disponible es >= 6"""
        return self.cantidad >= 4
    
    def reducir_stock(self, cantidad=1):
        """Reduce el stock en la cantidad especificada"""
        if self.cantidad >= cantidad:
            self.cantidad -= cantidad
            return True
        return False
    
    def aumentar_stock(self, cantidad=1):
        """Aumenta el stock en la cantidad especificada"""
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
    """Modelo para imÃ¡genes de productos"""
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

class TipoPromocion(db.Model):
    """Modelo para tipos de promociÃ³n"""
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

# Tablas de vinculación para promociones
promocion_productos_link = db.Table('promocion_productos_link',
    db.Column('promocion_id', db.Integer, db.ForeignKey('promociones_productos.id'), primary_key=True),
    db.Column('producto_id', db.Integer, db.ForeignKey('productos.id'), primary_key=True)
)

promocion_categorias_link = db.Table('promocion_categorias_link',
    db.Column('promocion_id', db.Integer, db.ForeignKey('promociones_productos.id'), primary_key=True),
    db.Column('categoria_id', db.Integer, db.ForeignKey('categorias.id'), primary_key=True)
)

class PromocionProducto(db.Model):
    """Modelo para promociones de productos"""
    __tablename__ = 'promociones_productos'
    
    id = db.Column(db.Integer, primary_key=True)
    alcance = db.Column(db.String(20), default='producto')  # 'producto', 'categoria', 'tienda'
    tipo_promocion_id = db.Column(db.Integer, db.ForeignKey('tipos_promocion.id'), nullable=False)
    valor = db.Column(db.Float)  # Porcentaje de descuento o cantidad para "llevas X paga Y"
    es_cupon = db.Column(db.Boolean, default=False)
    codigo = db.Column(db.String(50), unique=True, nullable=True) # Código del cupón (solo si es_cupon=True)
    envio_gratis = db.Column(db.Boolean, default=False) # Si es True, se aplica envío gratis al alcance de la promoción
    activa = db.Column(db.Boolean, default=True)
    fecha_inicio = db.Column(db.DateTime, nullable=False)
    fecha_fin = db.Column(db.DateTime, nullable=False)
    compra_minima = db.Column(db.Float, default=0.0)
    max_usos = db.Column(db.Integer, nullable=True) # None = ilimitado
    usos_actuales = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    tipo_promocion = db.relationship('TipoPromocion', backref='promociones')
    
    # Relaciones Many-to-Many para alcance flexible
    productos = db.relationship('Producto', secondary=promocion_productos_link, backref='promociones')
    categorias = db.relationship('Categoria', secondary=promocion_categorias_link, backref='promociones')
    
    def esta_activa(self):
        """Verifica si la promociÃ³n estÃ¡ activa en este momento"""
        ahora = datetime.utcnow()
        return self.activa and self.fecha_inicio <= ahora <= self.fecha_fin
    
    def calcular_descuento(self, cantidad, precio_unitario):
        """Calcula el descuento segÃºn el tipo de promociÃ³n"""
        if not self.esta_activa():
            return 0
        
        tipo = self.tipo_promocion.nombre
        
        if tipo == 'descuento_porcentaje':
            return (precio_unitario * cantidad * self.valor) / 100
        elif tipo == 'descuento_fijo':
            return self.valor * cantidad
        elif tipo == '2x1':
            # Llevas 2, pagas 1
            unidades_gratis = cantidad // 2
            return precio_unitario * unidades_gratis
        elif tipo == '3x2':
            # Llevas 3, pagas 2
            unidades_gratis = cantidad // 3
            return precio_unitario * unidades_gratis
        elif tipo.startswith('llevas_'):
            # Formato: "llevas_X_paga_Y"
            partes = tipo.split('_')
            if len(partes) >= 4:
                lleva = int(partes[1])
                paga = int(partes[3])
                unidades_gratis = (cantidad // lleva) * (lleva - paga)
                return precio_unitario * unidades_gratis
        
        return 0
    
    def to_dict(self):
        return {
            'id': self.id,
            'alcance': self.alcance,
            'tipo_promocion_id': self.tipo_promocion_id,
            'tipo_promocion_nombre': self.tipo_promocion.nombre if self.tipo_promocion else None,
            'valor': self.valor,
            'activa': self.activa,
            'esta_activa': self.esta_activa(),
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'fecha_fin': self.fecha_fin.isoformat() if self.fecha_fin else None,
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


class MetodoPago(db.Model):
    """Modelo para mÃ©todos de pago"""
    __tablename__ = 'metodos_pago'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)  # 'transferencia', 'tarjeta_debito', 'tarjeta_credito'
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'activo': self.activo
        }

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
    metodo_envio = db.Column(db.String(100))  # 'andreani', 'correo_argentino', 'tienda_nube'
    
    subtotal = db.Column(db.Float, nullable=False)
    descuento = db.Column(db.Float, default=0)
    costo_envio = db.Column(db.Float, default=0)
    total = db.Column(db.Float, nullable=False)
    
    estado = db.Column(db.String(50), default='pendiente_aprobacion')  # pendiente_aprobacion, confirmado, en_preparacion, enviado, entregado, cancelado
    notas = db.Column(db.Text)
    
    # Campos para aprobación de pedidos
    aprobado = db.Column(db.Boolean, default=False, nullable=False)
    fecha_expiracion = db.Column(db.DateTime, nullable=True)  # 5 días después de creación
    fecha_aprobacion = db.Column(db.DateTime, nullable=True)
    admin_aprobador_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    
    # Campos para pagos y seguimiento
    external_id = db.Column(db.String(100)) # ID de Mercado Pago
    comprobante_url = db.Column(db.String(500)) # Para transferencia
    codigo_pago_unico = db.Column(db.String(50)) # Para transferencia
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Índices para mejorar rendimiento de filtros y estadísticas
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


class Cliente(db.Model):
    """Modelo para clientes registrados (newsletter)"""
    __tablename__ = 'clientes'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True) # Puede ser NULL para clientes registrados solo por newsletter
    telefono = db.Column(db.String(50))
    telefono_verificado = db.Column(db.Boolean, default=False)
    metodo_verificacion = db.Column(db.String(20), default='telefono') # 'email' o 'telefono'
    codigo_verificacion = db.Column(db.String(6), nullable=True)
    acepta_newsletter = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Índices explícitos para búsqueda rápida
    __table_args__ = (
        db.Index('idx_cliente_email', 'email', unique=True),
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
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Shipment(db.Model):
    """Modelo para envÃ­os y tracking"""
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

class Favorito(db.Model):
    """Modelo para productos favoritos de clientes"""
    __tablename__ = 'favoritos'
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    cliente = db.relationship('Cliente', backref=db.backref('favoritos', lazy='dynamic'))
    producto = db.relationship('Producto')
    
    # Restricción única para evitar duplicados
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


class VentaExterna(db.Model):
    """Modelo para ventas realizadas fuera de la tienda web (ventas directas, telefónicas, etc.)"""
    __tablename__ = 'ventas_externas'
    
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    talle_id = db.Column(db.Integer, db.ForeignKey('talles.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    ganancia_total = db.Column(db.Float, nullable=False)  # cantidad * precio_unitario
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    notas = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    producto = db.relationship('Producto', backref='ventas_externas')
    talle = db.relationship('Talle', backref='ventas_externas')
    admin = db.relationship('Admin', backref='ventas_externas')
    
    # Índices para mejorar rendimiento de consultas
    __table_args__ = (
        db.Index('idx_venta_externa_producto', 'producto_id'),
        db.Index('idx_venta_externa_fecha', 'fecha'),
        db.Index('idx_venta_externa_admin', 'admin_id'),
        db.Index('idx_venta_externa_fecha_producto', 'fecha', 'producto_id'),  # Índice compuesto para filtros
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

class Carrito(db.Model):
    """Modelo para carrito de compras persistente"""
    __tablename__ = 'carritos'
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False, unique=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
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
    
    # Relaciones
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
