from flask import Blueprint, request, jsonify, send_from_directory, current_app
from extensions import limiter, mail
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_mail import Message
from cache_utils import cache, invalidate_cache, cached
from models import *
from sqlalchemy import or_, and_, desc
from datetime import datetime
import uuid
import os
import json
import logging
from threading import Thread
from services.product_service import ProductService
from services.order_service import OrderService

logger = logging.getLogger(__name__)
store_public_bp = Blueprint('store_public', __name__)

# ==================== PRODUCTOS ====================

@store_public_bp.route('/api/productos', methods=['GET'])
def get_productos():
    """Obtener productos con filtros y paginación (público) - REFACTORIZADO"""
    # CACHE ACTIVADO
    cache_key = f"productos:{request.query_string.decode()}"
    cached_result = cache.get(cache_key)
    if cached_result: return jsonify(cached_result), 200

    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 12, type=int)
    filters = request.args.to_dict()
    
    pagination = ProductService.get_catalog(filters, page, page_size)
    productos_db = pagination.items
    
    # --- OPTIMIZACIÓN: Pre-fetch de promociones para evitar N+1 ---
    from models.promociones import PromocionProducto
    ahora = datetime.utcnow()
    
    # 1. Promociones Globales (una sola consulta)
    global_promos = PromocionProducto.query.filter(
        PromocionProducto.alcance == 'tienda',
        PromocionProducto.activa == True,
        PromocionProducto.fecha_inicio <= ahora,
        or_(PromocionProducto.fecha_fin >= ahora, PromocionProducto.fecha_fin == None)
    ).all()
    
    # 2. Promociones por Categoría (una sola consulta para todas las categorías en la página)
    cat_ids = list(set([p.categoria_id for p in productos_db]))
    category_promos_list = PromocionProducto.query.filter(
        PromocionProducto.activa == True,
        PromocionProducto.fecha_inicio <= ahora,
        or_(PromocionProducto.fecha_fin >= ahora, PromocionProducto.fecha_fin == None),
        PromocionProducto.categorias.any(Categoria.id.in_(cat_ids))
    ).all()
    
    # Mapear promociones a sus categorías
    cat_promos_map = {}
    for promo in category_promos_list:
        for cat in promo.categorias:
            if cat.id not in cat_promos_map: cat_promos_map[cat.id] = []
            cat_promos_map[cat.id].append(promo)

    # 3. Serialización con contexto pre-cargado
    items_dict = []
    for p in productos_db:
        # Calcular promos activas combinando directas, categoría y globales
        active_promos = p.get_promociones_activas(global_promos=global_promos, category_promos=cat_promos_map)
        items_dict.append(p.to_dict(active_promos=active_promos))
    
    result = {
        'items': items_dict,
        'total': pagination.total,
        'page': page,
        'page_size': page_size,
        'pages': pagination.pages
    }
    
    cache.set(cache_key, result, ttl_seconds=300)
    return jsonify(result), 200

@store_public_bp.route('/api/productos/<int:id>', methods=['GET'])
def get_producto(id):
    """Obtener detalle de producto (público)"""
    producto = Producto.query.get_or_404(id)
    if not producto.activo:
        return jsonify({'error': 'Producto no disponible'}), 404
    return jsonify(producto.to_dict()), 200

# ==================== CATEGORÍAS ====================

@store_public_bp.route('/api/categorias', methods=['GET'])
# @cached(ttl_seconds=3600)
def get_categorias():
    include_subs = request.args.get('incluir_subcategorias', 'true') == 'true'
    padre_id = request.args.get('categoria_padre_id', type=int)
    flat = request.args.get('flat', 'false') == 'true'
    
    query = Categoria.query.options(joinedload(Categoria.categoria_padre))
    if padre_id:
        query = query.filter_by(id=padre_id) if flat else query.filter_by(categoria_padre_id=padre_id)
    elif not flat:
        query = query.filter_by(categoria_padre_id=None)
        
    categorias = query.order_by(Categoria.orden).all()
    return jsonify([c.to_dict(include_subcategorias=include_subs) for c in categorias]), 200

@store_public_bp.route('/api/categorias/tree', methods=['GET'])
# @cached(ttl_seconds=1) # Disabled cache temporarily to debug
def get_categorias_tree():
    try:
        try:
            # Intentar obtener con ordenamiento (puede fallar si falta la columna o migración)
            categorias_raiz = Categoria.query.filter_by(categoria_padre_id=None).order_by(Categoria.orden).all()
        except Exception as e_sort:
            logger.warning(f"Error ordenando categorías (posible falta de columna orden): {e_sort}")
            # Fallback sin ordenamiento
            categorias_raiz = Categoria.query.filter_by(categoria_padre_id=None).all()
            
        return jsonify([c.get_arbol_completo() for c in categorias_raiz]), 200
    except Exception as e:
        logger.error(f"Error en Categorias Tree: {str(e)}")
        return jsonify({'error': 'Error generando el árbol de categorías'}), 500

# ==================== TALLES Y COLORES ====================

@store_public_bp.route('/api/talles', methods=['GET'])
@cached(ttl_seconds=3600)
def get_talles():
    talles = Talle.query.all()
    orden = {'S':1, 'M':2, 'L':3, 'XL':4, 'XXL':5, 'XXXL':6}
    talles_s = sorted(talles, key=lambda t: orden.get(t.nombre.upper(), 99))
    # Filter out XS explicitly just in case
    talles_s = [t for t in talles_s if t.nombre != 'XS']
    return jsonify([t.to_dict() for t in talles_s]), 200

@store_public_bp.route('/api/colores', methods=['GET'])
@cached(ttl_seconds=3600)
def get_colores():
    colores = Color.query.all()
    return jsonify([c.to_dict() for c in colores]), 200

# ==================== PROMOCIONES ====================

@store_public_bp.route('/api/promociones', methods=['GET'])
def get_promociones():
    ahora = datetime.utcnow()
    promos = PromocionProducto.query.filter(
        PromocionProducto.activa == True,
        PromocionProducto.fecha_inicio <= ahora,
        or_(PromocionProducto.fecha_fin.is_(None), PromocionProducto.fecha_fin >= ahora)
    ).all()
    return jsonify([p.to_dict() for p in promos]), 200

@store_public_bp.route('/api/promociones/validar', methods=['POST'])
def validar_cupon():
    """Valida un código de cupón y devuelve sus beneficios"""
    data = request.json
    codigo = data.get('codigo')
    
    if not codigo:
        return jsonify({'error': 'Código requerido'}), 400
        
    promo = PromocionProducto.query.filter_by(codigo=codigo, es_cupon=True, activa=True).first()
    
    if not promo or not promo.esta_activa():
        return jsonify({'error': 'Cupón inválido o vencido'}), 404
        
    if promo.max_usos is not None and promo.usos_actuales >= promo.max_usos:
        return jsonify({'error': 'Cupón agotado'}), 400
        
    return jsonify({
        'valido': True,
        'promo': promo.to_dict()
    }), 200

# ==================== CHECKOUT ====================

@store_public_bp.route('/api/orders', methods=['POST', 'OPTIONS'])
@limiter.limit("3 per minute")
def create_pedido():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response, 200

    data = request.get_json()
    try:
        pedido = OrderService.create_order(data)
        db.session.commit()
        return jsonify(pedido.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error Checkout: {str(e)}")
        return jsonify({'error': str(e)}), 400

@store_public_bp.route('/api/metodos-pago', methods=['GET'])
@cached(ttl_seconds=3600)
def get_metodos_pago():
    metodos = MetodoPago.query.filter_by(activo=True).all()
    return jsonify([m.to_dict() for m in metodos]), 200

@store_public_bp.route('/api/envios/calcular', methods=['POST'])
def calcular_envio_route():
    from services.shipping_service import ShippingService
    
    # DEBUG: Log raw request data
    print(f"DEBUG ENDPOINT RAW: request.data={request.data}", flush=True)
    print(f"DEBUG ENDPOINT RAW: request.content_type={request.content_type}", flush=True)
    print(f"DEBUG ENDPOINT RAW: request.headers={dict(request.headers)}", flush=True)
    
    data = request.json
    print(f"DEBUG ENDPOINT JSON: request.json={data}", flush=True)
    
    if not data:
        print("ERROR: request.json is None - checking request.get_json()", flush=True)
        data = request.get_json(force=True, silent=True)
        print(f"DEBUG ENDPOINT FORCE: get_json(force=True)={data}", flush=True)
    
    if not data:
        return jsonify({"error": "No JSON data received"}), 400
    
    zip_code = data.get('codigo_postal')
    items = data.get('items', [])  # CRITICAL: Extract items from request
    
    print(f"DEBUG ENDPOINT: Received zip_code={zip_code}, items_count={len(items) if items else 0}", flush=True)
    print(f"DEBUG ENDPOINT: Items={items}", flush=True)
    
    if not zip_code:
        return jsonify({"error": "Código postal requerido"}), 400
        
    try:
        # CRITICAL: Pass items to calculate_cost
        options = ShippingService.calculate_cost(zip_code, items=items)
        
        metodo_solicitado = data.get('metodo_envio')
        if metodo_solicitado and metodo_solicitado != 'retiro':
            # Filtrar por el prefijo del ID (ej: 'andreani' matches 'andreani_sucursal')
            options = [opt for opt in options if opt['id'].startswith(metodo_solicitado)]
            
        return jsonify(options), 200
    except Exception as e:
        logger.error(f"Error calculando envío: {str(e)}")
        return jsonify({"error": "Error al calcular envío"}), 500

# ==================== CONTACTO ====================

@store_public_bp.route('/api/contacto', methods=['POST'])
def enviar_contacto():
    try:
        data = request.json
        nombre = data.get('nombre')
        email = data.get('email')
        mensaje = data.get('mensaje')
        telefono = data.get('telefono')
        
        print(f"DEBUG CONTACTO: Iniciando envío para {nombre} ({email}) - Tel: {telefono}", flush=True)
        
        if not all([nombre, email, mensaje]): 
            print("DEBUG CONTACTO: Error - Faltan campos obligatorios", flush=True)
            return jsonify({'error': 'Campos obligatorios'}), 400
    
        msg = Message(
            subject=f"Contacto Web: {nombre}",
            sender=current_app.config.get('MAIL_USERNAME'),
            recipients=[os.environ.get('CONTACT_EMAIL', 'elvestuario.r4@gmail.com')],
            body=f"Nombre: {nombre}\nEmail: {email}\nTeléfono: {telefono}\n\nMensaje:\n{mensaje}",
            reply_to=email
        )
        
        # Enviar email de forma asíncrona vía Brevo API
        def send_async_email(app, payload):
            with app.app_context():
                try:
                    import requests
                    api_key = os.environ.get('BREVO_API_KEY')
                    url = "https://api.brevo.com/v3/smtp/email"
                    
                    headers = {
                        "accept": "application/json",
                        "content-type": "application/json",
                        "api-key": api_key
                    }
                    
                    print(f"DEBUG CONTACTO [Brevo]: Enviando vía API a {payload['to'][0]['email']}...", flush=True)
                    response = requests.post(url, headers=headers, json=payload, timeout=15)
                    
                    if response.status_code in [201, 202, 200]:
                        print(f"DEBUG CONTACTO [Brevo]: ENVÍO EXITOSO. ID: {response.json().get('messageId')}", flush=True)
                    else:
                        print(f"DEBUG CONTACTO [Brevo]: FALLÓ. Código: {response.status_code}, Error: {response.text}", flush=True)
                        logging.error(f"Error Brevo API: {response.text}")
                except Exception as e:
                    print(f"DEBUG CONTACTO [Brevo]: Error general: {str(e)}", flush=True)
                    logging.error(f"Error en envío asíncrono Brevo: {str(e)}")

        # Preparar el payload para Brevo
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER', 'elvestuario.r4@gmail.com')
        recipient_email = os.environ.get('CONTACT_EMAIL', 'elvestuario.r4@gmail.com')
        
        brevo_payload = {
            "sender": {"name": "Web El Vestuario", "email": sender_email},
            "to": [{"email": recipient_email}],
            "subject": f"Contacto Web: {nombre}",
            "textContent": f"Nombre: {nombre}\nEmail: {email}\nTeléfono: {telefono}\n\nMensaje:\n{mensaje}",
            "replyTo": {"email": email}
        }

        print("DEBUG CONTACTO: Lanzando thread de envío asíncrono vía Brevo...", flush=True)
        Thread(target=send_async_email, args=(current_app._get_current_object(), brevo_payload)).start()
        
        return jsonify({'message': 'Ok, tu mensaje está siendo procesado.'}), 200

    except Exception as outer_e:
        print(f"DEBUG CONTACTO: Error CRÍTICO en la ruta: {str(outer_e)}", flush=True)
        logger.error(f"Error CRÍTICO en enviar_contacto: {str(outer_e)}")
        return jsonify({'error': 'Error interno en el servidor'}), 500

# ==================== CARRITO PERSISTENTE ====================

@store_public_bp.route('/api/cart', methods=['GET'])
@jwt_required()
def get_cart():
    """Obtiene el carrito persistente del usuario"""
    try:
        current_identity = get_jwt_identity() # Esto devuelve el ID o 'admin'
        # Asumimos que es un cliente logueado
        # get_jwt_identity puede devolver un string, asegurarnos que tenemos el cliente_id
        
        # En la implementación de login_cliente (auth.py), identity es el email o el id?
        # Revisando auth.py (no mostrado pero inferido): usualmente es el ID o subject.
        # Si get_jwt_identity devuelve el ID directamente:
        
        # Primero intentar obtener cliente por email si el identity es string no numérico
        cliente = None
        if isinstance(current_identity, str) and '@' in current_identity:
             cliente = Cliente.query.filter_by(email=current_identity).first()
        else:
             # Si es numérico o string numérico
             try:
                 cliente_id = int(current_identity)
                 cliente = Cliente.query.get(cliente_id)
             except:
                 pass
        
        # Si no encontramos cliente (quizás es un admin o token inválido para cliente)
        if not cliente:
            # Fallback: buscar en claims si JWT tiene info extra
            # Pero por ahora devolvemos vacío o error
             return jsonify({'items': []}), 200

        carrito = Carrito.query.filter_by(cliente_id=cliente.id).first()
        if not carrito:
            return jsonify({'items': [], 'updated_at': None}), 200
            
        # Verificar expiración (3 días = 72 horas)
        if carrito.updated_at:
            delta = datetime.utcnow() - carrito.updated_at
            if delta.total_seconds() > (72 * 3600):
                # Expirado: Limpiar items y devolver vacío
                ItemCarrito.query.filter_by(carrito_id=carrito.id).delete()
                # Actualizamos fecha para resetear (o lo dejamos viejo/null?)
                # Si borramos items, el carrito está "nuevo/vacío"
                carrito.updated_at = datetime.utcnow()
                db.session.commit()
                return jsonify({'items': [], 'updated_at': None}), 200

        # Formato compatible con frontend CartItem
        items = []
        for item in carrito.items:
            items.append({
                'producto': item.producto.to_dict(include_stock=True), # Importante el stock para validaciones
                'talle': item.talle.to_dict(),
                'cantidad': item.cantidad,
                'precio_unitario': item.producto.precio_base, # Siempre base, igual que frontend
                'descuento': 0 # Frontend recalcula descuentos dinámicos
            })
            
        return jsonify({
            'items': items,
            'updated_at': carrito.updated_at.isoformat() if carrito.updated_at else None
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching cart: {e}")
        return jsonify({'error': str(e)}), 500

@store_public_bp.route('/api/cart', methods=['POST'])
@jwt_required()
def sync_cart():
    """Sincroniza (sobreescribe) el carrito del usuario con el enviado"""
    try:
        data = request.get_json()
        new_items = data.get('items', [])
        
        current_identity = get_jwt_identity()
        cliente = None
        if isinstance(current_identity, str) and '@' in current_identity:
             cliente = Cliente.query.filter_by(email=current_identity).first()
        else:
             try:
                 cliente_id = int(current_identity)
                 cliente = Cliente.query.get(cliente_id)
             except:
                 pass
                 
        if not cliente:
            return jsonify({'error': 'Cliente no identificado'}), 401
            
        # Buscar o crear carrito
        carrito = Carrito.query.filter_by(cliente_id=cliente.id).first()
        if not carrito:
            carrito = Carrito(cliente_id=cliente.id)
            db.session.add(carrito)
            db.session.flush() # Para tener ID
            
        # Limpiar items anteriores (Estrategia simple: Replace All)
        # Podría optimizarse haciendo diff, pero replace es seguro para evitar inconsistencias
        ItemCarrito.query.filter_by(carrito_id=carrito.id).delete()
        
        # Agregar nuevos items
        for item in new_items:
            prod_id = item.get('producto', {}).get('id') or item.get('producto_id')
            talle_id = item.get('talle', {}).get('id') or item.get('talle_id')
            qty = item.get('cantidad', 1)
            
            if prod_id and talle_id and qty > 0:
                new_item = ItemCarrito(
                    carrito_id=carrito.id,
                    producto_id=int(prod_id),
                    talle_id=int(talle_id),
                    cantidad=int(qty)
                )
                db.session.add(new_item)
        
        carrito.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'Carrito sincronizado', 'count': len(new_items)}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error syncing cart: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== ESTÁTICOS ====================

@store_public_bp.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
