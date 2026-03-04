"""
Blueprint de ventas externas (admin).
Rutas: /api/admin/ventas-externas
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from cache_utils import invalidate_cache
from models import VentaExterna, Producto, Talle, StockTalle, Admin, db
from datetime import datetime

ventas_externas_bp = Blueprint('admin_ventas_externas', __name__)


@ventas_externas_bp.route('/api/admin/ventas-externas', methods=['POST'])
@jwt_required()
def crear_venta_externa():
    try:
        data = request.get_json()
        required_fields = ['producto_id', 'talle_id', 'cantidad', 'precio_unitario']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo requerido: {field}'}), 400

        producto_id = int(data['producto_id'])
        talle_id = int(data['talle_id'])
        cantidad = int(data['cantidad'])
        precio_unitario = float(data['precio_unitario'])

        if cantidad <= 0:
            return jsonify({'error': 'La cantidad debe ser mayor a 0'}), 400
        if precio_unitario <= 0:
            return jsonify({'error': 'El precio unitario debe ser mayor a 0'}), 400

        producto = Producto.query.get(producto_id)
        if not producto:
            return jsonify({'error': 'Producto no encontrado'}), 404
        talle = Talle.query.get(talle_id)
        if not talle:
            return jsonify({'error': 'Talle no encontrado'}), 404

        stock_talle = StockTalle.query.filter_by(producto_id=producto_id, talle_id=talle_id).first()
        if not stock_talle or stock_talle.cantidad < cantidad:
            return jsonify({
                'error': f'Stock insuficiente para {producto.nombre} talle {talle.nombre}. Disponible: {stock_talle.cantidad if stock_talle else 0}'
            }), 400

        admin_id = get_jwt_identity()
        admin = Admin.query.get(int(admin_id))
        if not admin:
            return jsonify({'error': 'Admin no encontrado (sesión inválida)'}), 404

        ganancia_total = cantidad * precio_unitario
        venta = VentaExterna(
            producto_id=producto_id, talle_id=talle_id, cantidad=cantidad,
            precio_unitario=precio_unitario, ganancia_total=ganancia_total,
            fecha=datetime.utcnow(), admin_id=admin.id, notas=data.get('notas', '')
        )
        stock_talle.reducir_stock(cantidad)
        producto.ventas_count = (producto.ventas_count or 0) + cantidad
        db.session.add(venta)
        db.session.commit()
        invalidate_cache(pattern='estadisticas')
        invalidate_cache(pattern='productos')
        return jsonify({'message': 'Venta externa registrada exitosamente', 'venta': venta.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@ventas_externas_bp.route('/api/admin/ventas-externas', methods=['GET'])
@jwt_required()
def listar_ventas_externas():
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)
        producto_id = request.args.get('producto_id', type=int)
        categoria_id = request.args.get('categoria_id', type=int)
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')

        query = VentaExterna.query
        if categoria_id:
            query = query.join(Producto).filter(Producto.categoria_id == categoria_id)
        if producto_id:
            query = query.filter_by(producto_id=producto_id)
        if fecha_desde:
            query = query.filter(VentaExterna.fecha >= datetime.strptime(fecha_desde, '%Y-%m-%d'))
        if fecha_hasta:
            fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(VentaExterna.fecha <= fecha_hasta_dt)

        query = query.order_by(VentaExterna.fecha.desc())
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        return jsonify({
            'items': [v.to_dict() for v in pagination.items],
            'total': pagination.total, 'page': page,
            'page_size': page_size, 'pages': pagination.pages
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ventas_externas_bp.route('/api/admin/ventas-externas/<int:venta_id>', methods=['DELETE'])
@jwt_required()
def eliminar_venta_externa(venta_id):
    try:
        venta = VentaExterna.query.get_or_404(venta_id)
        stock_talle = StockTalle.query.filter_by(producto_id=venta.producto_id, talle_id=venta.talle_id).first()
        if stock_talle:
            stock_talle.aumentar_stock(venta.cantidad)
        producto = Producto.query.get(venta.producto_id)
        if producto and producto.ventas_count:
            producto.ventas_count = max(0, producto.ventas_count - venta.cantidad)
        db.session.delete(venta)
        db.session.commit()
        invalidate_cache(pattern='estadisticas')
        invalidate_cache(pattern='productos')
        return jsonify({'message': 'Venta externa eliminada y stock restaurado'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
