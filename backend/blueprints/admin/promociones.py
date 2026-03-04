"""
Blueprint de promociones y cupones (admin).
Rutas: /api/admin/promociones, /api/admin/tipos-promocion
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from cache_utils import invalidate_cache
from models import PromocionProducto, TipoPromocion, Producto, Categoria, db
from datetime import datetime

promociones_bp = Blueprint('admin_promociones', __name__)


@promociones_bp.route('/api/admin/tipos-promocion', methods=['GET'])
@jwt_required()
def get_tipos_promocion():
    tipos = TipoPromocion.query.all()
    return jsonify([t.to_dict() for t in tipos]), 200


@promociones_bp.route('/api/admin/promociones', methods=['GET'])
@jwt_required()
def get_promociones():
    promociones = PromocionProducto.query.order_by(PromocionProducto.fecha_inicio.desc()).all()
    return jsonify([p.to_dict() for p in promociones]), 200


@promociones_bp.route('/api/admin/promociones', methods=['POST'])
@jwt_required()
def create_promocion():
    data = request.get_json()
    try:
        codigo = data.get('codigo')
        if not codigo or not str(codigo).strip():
            codigo = None
        else:
            codigo = str(codigo).strip().upper()

        promocion = PromocionProducto(
            alcance=data.get('alcance', 'producto'),
            tipo_promocion_id=data['tipo_promocion_id'],
            valor=float(data.get('valor', 0)),
            activa=data.get('activa', True),
            fecha_inicio=datetime.fromisoformat(data['fecha_inicio'].replace('Z', '+00:00')),
            fecha_fin=datetime.fromisoformat(data['fecha_fin'].replace('Z', '+00:00')),
            es_cupon=data.get('es_cupon', False),
            codigo=codigo,
            envio_gratis=data.get('envio_gratis', False),
            compra_minima=float(data.get('compra_minima', 0))
        )
        if data.get('productos_ids'):
            promocion.productos = Producto.query.filter(Producto.id.in_(data['productos_ids'])).all()
        if data.get('categorias_ids'):
            promocion.categorias = Categoria.query.filter(Categoria.id.in_(data['categorias_ids'])).all()
        db.session.add(promocion)
        db.session.commit()
        invalidate_cache(pattern='productos')
        return jsonify(promocion.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@promociones_bp.route('/api/admin/promociones/<int:id>', methods=['PUT', 'DELETE'])
@jwt_required()
def manage_promocion(id):
    promocion = PromocionProducto.query.get_or_404(id)
    if request.method == 'DELETE':
        try:
            db.session.delete(promocion)
            db.session.commit()
            invalidate_cache(pattern='productos')
            return jsonify({'message': 'Promoción eliminada'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    data = request.get_json()
    try:
        if 'alcance' in data: promocion.alcance = data['alcance']
        if 'tipo_promocion_id' in data: promocion.tipo_promocion_id = data['tipo_promocion_id']
        if 'valor' in data: promocion.valor = float(data['valor'])
        if 'activa' in data: promocion.activa = data['activa']
        if 'fecha_inicio' in data:
            promocion.fecha_inicio = datetime.fromisoformat(data['fecha_inicio'].replace('Z', '+00:00'))
        if 'fecha_fin' in data:
            promocion.fecha_fin = datetime.fromisoformat(data['fecha_fin'].replace('Z', '+00:00'))
        if 'es_cupon' in data: promocion.es_cupon = data['es_cupon']
        if 'codigo' in data:
            codigo = data['codigo']
            promocion.codigo = str(codigo).strip().upper() if codigo and str(codigo).strip() else None
        if 'envio_gratis' in data: promocion.envio_gratis = data['envio_gratis']
        if 'compra_minima' in data: promocion.compra_minima = float(data['compra_minima'])
        if 'productos_ids' in data:
            promocion.productos = Producto.query.filter(Producto.id.in_(data['productos_ids'])).all()
        if 'categorias_ids' in data:
            promocion.categorias = Categoria.query.filter(Categoria.id.in_(data['categorias_ids'])).all()
        db.session.commit()
        invalidate_cache(pattern='productos')
        return jsonify(promocion.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
