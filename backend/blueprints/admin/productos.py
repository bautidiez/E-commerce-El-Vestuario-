"""
Blueprint de gestión de productos (admin).
Rutas: /api/admin/productos, /api/admin/products/search, /api/admin/imagenes
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
from cache_utils import cache, invalidate_cache
from models import Producto, Categoria, ImagenProducto, db
from extensions import limiter
from PIL import Image
from pathlib import Path
import uuid, os, logging

logger = logging.getLogger(__name__)
productos_bp = Blueprint('admin_productos', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@productos_bp.route('/api/admin/products/search', methods=['GET'])
@jwt_required()
def search_products():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([]), 200
    try:
        productos = Producto.query.filter(
            Producto.nombre.ilike(f'%{query}%')
        ).limit(20).all()
        return jsonify([{
            'id': p.id, 'nombre': p.nombre,
            'precio_base': p.precio_base, 'precio_actual': p.get_precio_actual(),
            'color': p.color, 'color_hex': p.color_hex,
            'imagen_principal': p.imagenes[0].url if p.imagenes else None
        } for p in productos]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@productos_bp.route('/api/admin/productos', methods=['POST'])
@jwt_required()
def create_producto():
    data = request.get_json()
    if not data.get('nombre') or not data.get('categoria_id') or not data.get('precio_base'):
        return jsonify({'error': 'Faltan campos requeridos (nombre, categoria_id, precio_base)'}), 400

    max_retries = 2
    for attempt in range(max_retries):
        try:
            producto = Producto(
                nombre=data['nombre'],
                descripcion=data.get('descripcion', ''),
                categoria_id=int(data['categoria_id']),
                precio_base=float(data['precio_base']),
                precio_descuento=float(data['precio_descuento']) if data.get('precio_descuento') else None,
                destacado=data.get('destacado', False),
                activo=data.get('activo', True),
                color=data.get('color'),
                color_hex=data.get('color_hex'),
                dorsal=data.get('dorsal'),
                numero=int(data['numero']) if data.get('numero') not in (None, '') else None,
                version=data.get('version'),
                producto_relacionado_id=int(data['producto_relacionado_id']) if data.get('producto_relacionado_id') else None
            )
            if 'productos_relacionados' in data and isinstance(data['productos_relacionados'], list):
                for rel_id in data['productos_relacionados']:
                    rel_prod = Producto.query.get(rel_id)
                    if rel_prod:
                        producto.relacionados.append(rel_prod)
                        if producto not in rel_prod.relacionados:
                            rel_prod.relacionados.append(producto)
            db.session.add(producto)
            db.session.commit()
            invalidate_cache(pattern='productos')
            return jsonify(producto.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            err_str = str(e)
            if attempt < max_retries - 1 and ('UniqueViolation' in err_str or 'duplicate key' in err_str or 'pkey' in err_str):
                try:
                    from sqlalchemy import text
                    db.session.execute(text("SELECT setval('productos_id_seq', COALESCE((SELECT MAX(id) FROM productos), 1))"))
                    db.session.commit()
                    continue
                except:
                    pass
            return jsonify({'error': err_str}), 500


@productos_bp.route('/api/admin/productos/bulk', methods=['DELETE'])
@jwt_required()
def bulk_delete_productos():
    from models import ItemPedido, VentaExterna
    data = request.get_json()
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'error': 'No se proporcionaron IDs'}), 400
    
    resultados = {
        'eliminados': [],
        'errores': []
    }
    
    for id in ids:
        try:
            producto = Producto.query.get(id)
            if not producto:
                resultados['errores'].append({'id': id, 'error': 'Producto no encontrado'})
                continue
                
            # Verificar dependencias
            pedidos_count = ItemPedido.query.filter_by(producto_id=id).count()
            if pedidos_count > 0:
                resultados['errores'].append({'id': id, 'nombre': producto.nombre, 'error': f'Tiene {pedidos_count} pedido(s) asociado(s)'})
                continue
                
            ventas_count = VentaExterna.query.filter_by(producto_id=id).count()
            if ventas_count > 0:
                resultados['errores'].append({'id': id, 'nombre': producto.nombre, 'error': f'Tiene {ventas_count} venta(s) asociada(s)'})
                continue
                
            # Si tiene promociones, removerlo
            if hasattr(producto, 'promociones'):
                for promo in producto.promociones:
                    promo.productos.remove(producto)
            
            nombre_prod = producto.nombre
            db.session.delete(producto)
            resultados['eliminados'].append({'id': id, 'nombre': nombre_prod})
        except Exception as e:
            resultados['errores'].append({'id': id, 'error': str(e)})
            
    try:
        db.session.commit()
        invalidate_cache(pattern='productos')
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al confirmar cambios: {str(e)}'}), 500
        
    return jsonify(resultados), 200


@productos_bp.route('/api/admin/productos/<int:id>', methods=['PUT', 'DELETE'])
@jwt_required()
def manage_product(id):
    from models import ItemPedido, VentaExterna
    producto = Producto.query.get_or_404(id)
    if request.method == 'DELETE':
        try:
            pedidos_count = ItemPedido.query.filter_by(producto_id=id).count()
            if pedidos_count > 0:
                return jsonify({'error': f'No se puede eliminar "{producto.nombre}" porque tiene {pedidos_count} pedido(s) asociado(s).', 'suggestion': 'desactivar', 'relacion': 'pedidos', 'count': pedidos_count}), 400
            ventas_count = VentaExterna.query.filter_by(producto_id=id).count()
            if ventas_count > 0:
                return jsonify({'error': f'No se puede eliminar "{producto.nombre}" porque tiene {ventas_count} venta(s) externa(s).', 'suggestion': 'desactivar', 'relacion': 'ventas_externas', 'count': ventas_count}), 400
            if hasattr(producto, 'promociones'):
                for promo in producto.promociones:
                    promo.productos.remove(producto)
            db.session.delete(producto)
            db.session.commit()
            invalidate_cache(pattern='productos')
            return jsonify({'message': 'Producto eliminado'}), 200
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            if 'foreign key' in error_msg.lower() or 'violates' in error_msg.lower():
                return jsonify({'error': f'No se puede eliminar "{producto.nombre}" porque tiene datos relacionados.', 'suggestion': 'desactivar'}), 400
            return jsonify({'error': error_msg}), 500

    data = request.get_json()
    try:
        if 'nombre' in data: producto.nombre = data['nombre']
        if 'descripcion' in data: producto.descripcion = data['descripcion']
        if 'precio_base' in data: producto.precio_base = float(data['precio_base'])
        if 'precio_descuento' in data:
            producto.precio_descuento = float(data['precio_descuento']) if data['precio_descuento'] else None
        if 'categoria_id' in data: producto.categoria_id = int(data['categoria_id'])
        if 'activo' in data: producto.activo = data['activo']
        if 'destacado' in data: producto.destacado = data['destacado']
        if 'color' in data: producto.color = data['color']
        if 'color_hex' in data: producto.color_hex = data['color_hex']
        if 'dorsal' in data: producto.dorsal = data['dorsal']
        if 'numero' in data:
            producto.numero = int(data['numero']) if data['numero'] not in (None, '') else None
        if 'version' in data: producto.version = data['version']
        if 'producto_relacionado_id' in data:
            producto.producto_relacionado_id = int(data['producto_relacionado_id']) if data['producto_relacionado_id'] else None
        if 'productos_relacionados' in data and isinstance(data['productos_relacionados'], list):
            nuevos_relacionados = []
            for rel_id in data['productos_relacionados']:
                p = Producto.query.get(rel_id)
                if p:
                    nuevos_relacionados.append(p)
                    if producto not in p.relacionados:
                        p.relacionados.append(producto)
            producto.relacionados = nuevos_relacionados
        db.session.commit()
        invalidate_cache(pattern='productos')
        return jsonify(producto.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ── Imágenes ──────────────────────────────────────────────────────────────────

@productos_bp.route('/api/admin/productos/<int:producto_id>/imagenes', methods=['POST'])
@jwt_required()
def upload_imagen(producto_id):
    if 'imagen' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['imagen']
    if file and allowed_file(file.filename):
        try:
            img = Image.open(file)
            if img.width > 1200 or img.height > 1200:
                img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
            webp_filename = f"{uuid.uuid4()}.webp"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], webp_filename)
            img.save(filepath, 'WEBP', quality=85)
            es_principal = request.form.get('es_principal') == 'true'
            orden = int(request.form.get('orden', 0))
            
            # Si la nueva imagen va a ser principal, desmarcar las anteriores
            if es_principal:
                ImagenProducto.query.filter_by(producto_id=producto_id).update({'es_principal': False})
                db.session.flush()
            
            imagen = ImagenProducto(
                producto_id=producto_id,
                url=f"/static/uploads/{webp_filename}",
                es_principal=es_principal,
                orden=orden
            )
            db.session.add(imagen)
            db.session.commit()
            invalidate_cache(pattern='productos')
            return jsonify(imagen.to_dict()), 201
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return jsonify({'error': 'Error al procesar la imagen'}), 500
    return jsonify({'error': 'Invalid file'}), 400


@productos_bp.route('/api/admin/imagenes/<int:imagen_id>', methods=['PUT', 'DELETE'])
@jwt_required()
def manage_imagen(imagen_id):
    imagen = ImagenProducto.query.get_or_404(imagen_id)
    
    if request.method == 'DELETE':
        db.session.delete(imagen)
        db.session.commit()
        invalidate_cache(pattern='productos')
        return jsonify({'message': 'Deleted'}), 200

    data = request.get_json()
    try:
        if 'es_principal' in data:
            nuevo_valor = data['es_principal']
            if nuevo_valor == True:
                # Ponemos todas las otras a False primero
                ImagenProducto.query.filter_by(producto_id=imagen.producto_id).update({'es_principal': False})
            imagen.es_principal = nuevo_valor

        if 'orden' in data:
            imagen.orden = int(data['orden'])

        db.session.commit()
        invalidate_cache(pattern='productos')
        return jsonify(imagen.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

