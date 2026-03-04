"""
Blueprint de gestión de stock (admin).
Rutas: /api/admin/stock, /api/admin/stock/<id>, /api/admin/stock/add
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from models import StockTalle, Producto, Talle, db

stock_bp = Blueprint('admin_stock', __name__)


@stock_bp.route('/api/admin/stock', methods=['GET', 'POST'])
@jwt_required()
def manage_stock():
    if request.method == 'POST':
        data = request.get_json()
        try:
            existing = StockTalle.query.filter_by(
                producto_id=data['producto_id'],
                talle_id=data['talle_id']
            ).first()
            if existing:
                existing.cantidad = int(data['cantidad'])
                if 'color_id' in data:
                    existing.color_id = data['color_id']
            else:
                stock = StockTalle(
                    producto_id=data['producto_id'],
                    talle_id=data['talle_id'],
                    cantidad=int(data['cantidad']),
                    color_id=data.get('color_id')
                )
                db.session.add(stock)
            db.session.commit()
            return jsonify({'message': 'Stock actualizado'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)
    query = StockTalle.query.join(Producto).join(Talle)

    producto_id = request.args.get('producto_id', type=int)
    if producto_id:
        query = query.filter(StockTalle.producto_id == producto_id)

    categoria_id = request.args.get('categoria_id', type=int)
    if categoria_id:
        query = query.filter(Producto.categoria_id == categoria_id)

    talle_nombre = request.args.get('talle_nombre')
    if talle_nombre:
        query = query.filter(Talle.nombre == talle_nombre)

    search = request.args.get('search')
    if search:
        query = query.filter(Producto.nombre.ilike(f"%{search}%"))

    solo_agotado = request.args.get('solo_agotado')
    if str(solo_agotado).lower() == 'true':
        query = query.filter(StockTalle.cantidad == 0)

    solo_bajo = request.args.get('solo_bajo')
    if str(solo_bajo).lower() == 'true':
        umbral = request.args.get('umbral', 3, type=int)
        query = query.filter(StockTalle.cantidad > 0, StockTalle.cantidad <= umbral)

    ordenar_por = request.args.get('ordenar_por', 'alfabetico')
    if ordenar_por == 'alfabetico':
        query = query.order_by(Producto.nombre.asc())
    elif ordenar_por == 'alfabetico_desc':
        query = query.order_by(Producto.nombre.desc())
    elif ordenar_por == 'talle':
        query = query.order_by(Talle.orden.asc(), Producto.nombre.asc())
    elif ordenar_por == 'stock_asc':
        query = query.order_by(StockTalle.cantidad.asc())
    elif ordenar_por == 'stock_desc':
        query = query.order_by(StockTalle.cantidad.desc())

    pagination = query.paginate(page=page, per_page=page_size)
    return jsonify({
        'items': [s.to_dict() for s in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page
    }), 200


@stock_bp.route('/api/admin/stock/<int:id>', methods=['PUT', 'DELETE'])
@jwt_required()
def manage_single_stock(id):
    stock = StockTalle.query.get_or_404(id)
    if request.method == 'DELETE':
        try:
            db.session.delete(stock)
            db.session.commit()
            return jsonify({'message': 'Stock eliminado'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    data = request.get_json()
    try:
        if 'cantidad' in data: stock.cantidad = int(data['cantidad'])
        if 'color_id' in data: stock.color_id = data['color_id']
        if 'talle_id' in data: stock.talle_id = data['talle_id']
        db.session.commit()
        return jsonify(stock.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@stock_bp.route('/api/admin/stock/add', methods=['POST'])
@jwt_required()
def add_stock_by_sizes():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        increments = data.get('increments', {})
        if not product_id:
            return jsonify({'error': 'product_id es requerido'}), 400
        if not increments:
            return jsonify({'error': 'increments es requerido'}), 400
        producto = Producto.query.get(product_id)
        if not producto:
            return jsonify({'error': 'Producto no encontrado'}), 404

        updated_sizes = []
        for size_name, quantity in increments.items():
            if quantity <= 0:
                continue
            talle = Talle.query.filter_by(nombre=size_name).first()
            if not talle:
                continue
            stock = StockTalle.query.filter_by(producto_id=product_id, talle_id=talle.id).first()
            if stock:
                stock.cantidad += int(quantity)
            else:
                stock = StockTalle(producto_id=product_id, talle_id=talle.id, cantidad=int(quantity))
                db.session.add(stock)
            updated_sizes.append({'talle': size_name, 'nueva_cantidad': stock.cantidad})

        db.session.commit()
        return jsonify({'message': 'Stock actualizado exitosamente', 'updated': updated_sizes}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
