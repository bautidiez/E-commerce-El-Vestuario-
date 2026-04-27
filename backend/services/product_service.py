from models import Producto, Categoria, Color, StockTalle, db
from sqlalchemy import or_, case, select, exists, and_
from extensions import limiter
from cache_utils import cached

from sqlalchemy.orm import joinedload, selectinload

class ProductService:
    @staticmethod
    @cached(ttl_seconds=300) # Cache por 5 minutos
    def get_catalog(filters: dict, page: int = 1, page_size: int = 12):
        """
        Lógica centralizada para obtener productos con filtros complejos.
        """
        query = Producto.query.options(
            joinedload(Producto.categoria).joinedload(Categoria.categoria_padre),
            selectinload(Producto.imagenes),
            selectinload(Producto.stock_talles)
        )
        
        # Filtro de activos por defecto
        if filters.get('activos') != 'false':
            query = query.filter_by(activo=True)
            
        # Búsqueda textual
        busqueda = filters.get('busqueda')
        if busqueda:
            search_term = f"%{busqueda}%"
            query = query.filter(or_(
                Producto.nombre.ilike(search_term),
                Producto.descripcion.ilike(search_term)
            ))
            
        # Categorías (Recursivo - Optimizado)
        categoria_id = filters.get('categoria_id')
        if categoria_id:
            # Obtener todas las categorías una sola vez para evitar recursión en DB
            todas_categorias = Categoria.query.all()
            cat_map = {}
            for c in todas_categorias:
                if c.categoria_padre_id not in cat_map:
                    cat_map[c.categoria_padre_id] = []
                cat_map[c.categoria_padre_id].append(c.id)
            
            def get_all_child_ids(p_id):
                results = [p_id]
                if p_id in cat_map:
                    for child_id in cat_map[p_id]:
                        results.extend(get_all_child_ids(child_id))
                return results
            
            child_ids = get_all_child_ids(int(categoria_id))
            query = query.filter(Producto.categoria_id.in_(child_ids))
            
        # Otros filtros...
        if filters.get('destacados') == 'true':
            query = query.filter_by(destacado=True)
        
        # Filtro de ofertas: productos con precio_descuento O con promociones activas
        if filters.get('ofertas') == 'true':
            from datetime import datetime
            from models import PromocionProducto, promocion_productos_link, promocion_categorias_link
            ahora = datetime.utcnow()
            
            # Opción 1: Productos con precio_descuento
            tiene_descuento = (
                (Producto.precio_descuento.isnot(None)) &
                (Producto.precio_descuento > 0)
            )
            
            # Subconsulta para promociones activas
            active_promos_query = db.session.query(PromocionProducto.id).filter(
                PromocionProducto.activa == True,
                PromocionProducto.fecha_inicio <= ahora,
                or_(PromocionProducto.fecha_fin >= ahora, PromocionProducto.fecha_fin == None)
            ).subquery()

            # Opción 2: Productos con promociones activas (directas)
            tiene_promo_directa = Producto.id.in_(
                db.session.query(promocion_productos_link.c.producto_id).filter(
                    promocion_productos_link.c.promocion_id.in_(active_promos_query)
                )
            )
            
            # Opción 3: Productos cuya categoría tiene promociones activas
            tiene_promo_categoria = Producto.categoria_id.in_(
                db.session.query(promocion_categorias_link.c.categoria_id).filter(
                    promocion_categorias_link.c.promocion_id.in_(active_promos_query)
                )
            )
            
            # Combinar todas las condiciones con OR
            query = query.filter(or_(tiene_descuento, tiene_promo_directa, tiene_promo_categoria))
            
        if filters.get('precio_min'):
            query = query.filter(Producto.precio_base >= float(filters['precio_min']))
        if filters.get('precio_max'):
            query = query.filter(Producto.precio_base <= float(filters['precio_max']))

        # Filtro de estado de stock (Optimizado)
        estado_stock = filters.get('estado_stock')
        if estado_stock:
            if estado_stock == 'disponible':
                query = query.filter(Producto.id.in_(
                    db.session.query(StockTalle.producto_id).filter(StockTalle.cantidad >= 4)
                ))
            elif estado_stock == 'bajo':
                # Productos que tienen algún stock entre 1-3 Y NINGUNO >= 4
                productos_alto = db.session.query(StockTalle.producto_id).filter(StockTalle.cantidad >= 4)
                query = query.filter(
                    Producto.id.in_(db.session.query(StockTalle.producto_id).filter(StockTalle.cantidad.between(1, 3))),
                    ~Producto.id.in_(productos_alto)
                )
            elif estado_stock == 'no_disponible':
                productos_con_stock = db.session.query(StockTalle.producto_id).filter(StockTalle.cantidad > 0)
                query = query.filter(~Producto.id.in_(productos_con_stock))

        # Filtro de versión
        if filters.get('version'):
            query = query.filter(Producto.version == filters['version'])

        # Ordenamiento GLOBAL: Agotados siempre al final (Strict) - OPTIMIZADO con JOIN
        stock_subquery = db.session.query(
            StockTalle.producto_id,
            db.func.sum(StockTalle.cantidad).label('total_stock')
        ).group_by(StockTalle.producto_id).subquery()
        
        query = query.outerjoin(stock_subquery, Producto.id == stock_subquery.c.producto_id)
        
        stock_priority = case(
            (stock_subquery.c.total_stock > 0, 1),
            else_=2
        )
        
        query = query.order_by(stock_priority.asc())

        # Ordenamiento secundario (usuario)
        orden = filters.get('ordenar_por', 'nuevo')
        
        # Si hay búsqueda, priorizar por relevancia
        if busqueda and orden == 'nuevo':
            search_term = f"%{busqueda}%"
            query = query.order_by(
                case(
                    (Producto.nombre.ilike(search_term), 1),
                    (Producto.descripcion.ilike(search_term), 2),
                    else_=3
                ).asc(),
                Producto.created_at.desc()
            )
        elif orden == 'precio_asc':
            query = query.order_by(Producto.precio_base.asc())
        elif orden == 'precio_desc':
            query = query.order_by(Producto.precio_base.desc())
        elif orden == 'nombre_asc':
            query = query.order_by(Producto.nombre.asc())
        elif orden == 'nombre_desc':
            query = query.order_by(Producto.nombre.desc())
        elif orden == 'destacado':
            # Implementamos el orden de prioridad: 1. Destacados, 2. Ofertas, 3. Otros
            # Definimos qué es una "oferta" para el ordenamiento (misma lógica que el filtro de ofertas)
            from datetime import datetime
            from models import PromocionProducto, promocion_productos_link, promocion_categorias_link
            ahora = datetime.utcnow()
            
            # Opción 1: Productos con precio_descuento
            tiene_descuento = (Producto.precio_descuento > 0)
            
            # Opción 2: Productos con promociones activas (directas)
            tiene_promo_directa = Producto.id.in_(
                db.session.query(promocion_productos_link.c.producto_id).join(
                    PromocionProducto, PromocionProducto.id == promocion_productos_link.c.promocion_id
                ).filter(
                    PromocionProducto.activa == True,
                    PromocionProducto.fecha_inicio <= ahora,
                    or_(PromocionProducto.fecha_fin >= ahora, PromocionProducto.fecha_fin == None)
                )
            )
            
            # Opción 3: Productos con promociones por categoría
            tiene_promo_categoria = Producto.categoria_id.in_(
                db.session.query(promocion_categorias_link.c.categoria_id).join(
                    PromocionProducto, PromocionProducto.id == promocion_categorias_link.c.promocion_id
                ).filter(
                    PromocionProducto.activa == True,
                    PromocionProducto.fecha_inicio <= ahora,
                    or_(PromocionProducto.fecha_fin >= ahora, PromocionProducto.fecha_fin == None)
                )
            )

            is_offer = or_(tiene_descuento, tiene_promo_directa, tiene_promo_categoria)

            query = query.order_by(
                case(
                    (Producto.destacado == True, 1),
                    (is_offer, 2),
                    else_=3
                ).asc(),
                Producto.created_at.desc()
            )
        else:
            query = query.order_by(Producto.created_at.desc())
            
        return query.paginate(page=page, per_page=page_size, error_out=False)


    @staticmethod
    def get_by_id(product_id: int):
        return Producto.query.get(product_id)
