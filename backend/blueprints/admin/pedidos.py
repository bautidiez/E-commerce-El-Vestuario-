"""
Blueprint de gestión de pedidos (admin).
Rutas: /api/admin/pedidos, /api/admin/notas
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from cache_utils import invalidate_cache
from models import Pedido, NotaPedido, StockTalle, Producto, Talle, Admin, db
from datetime import datetime

pedidos_bp = Blueprint('admin_pedidos', __name__)


@pedidos_bp.route('/api/admin/pedidos', methods=['GET'])
@jwt_required()
def get_all_pedidos():
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 40, type=int)
        estado = request.args.get('estado')
        aprobado = request.args.get('aprobado')
        q = request.args.get('q')

        from models import VentaExterna
        
        # 1. Fetch Pedidos
        query_pedidos = Pedido.query
        if estado:
            query_pedidos = query_pedidos.filter_by(estado=estado)
        if aprobado is not None:
            query_pedidos = query_pedidos.filter_by(aprobado=aprobado.lower() == 'true')
        if q:
            search = f"%{q}%"
            query_pedidos = query_pedidos.filter(
                (Pedido.cliente_nombre.ilike(search)) |
                (Pedido.cliente_email.ilike(search)) |
                (Pedido.numero_pedido.ilike(search))
            )
        
        # 2. Fetch Ventas Externas (only if no specific web-only state/approval is requested)
        ventas_externas_list = []
        if not estado or estado == 'entregado': # Assuming external sales are 'delivered'
            if aprobado is None or aprobado.lower() == 'true':
                query_ext = VentaExterna.query
                if q:
                    search = f"%{q}%"
                    # Search by product name if linked
                    query_ext = query_ext.join(Producto).filter(Producto.nombre.ilike(search))
                
                # Fetch recent external sales
                ventas_externas = query_ext.order_by(VentaExterna.fecha.desc()).limit(100).all()
                for ve in ventas_externas:
                    ventas_externas_list.append({
                        'id': f"ext_{ve.id}",
                        'numero_pedido': 'Externa',
                        'cliente_nombre': 'Registro Externo',
                        'cliente_email': ve.admin.username if ve.admin else '-',
                        'total': ve.ganancia_total,
                        'estado': 'entregado',
                        'aprobado': True,
                        'created_at': ve.fecha.isoformat(),
                        'tipo': 'externa',
                        'item_count': ve.cantidad,
                        'notas': ve.notas,
                        'db_id': ve.id # Original ID
                    })

        # 3. Get Web Pedidos items
        web_pedidos = [p.to_dict() for p in query_pedidos.order_by(Pedido.created_at.desc()).limit(200).all()]
        for p in web_pedidos: p['tipo'] = 'web'

        # 4. Merge and Sort
        combined = sorted(web_pedidos + ventas_externas_list, key=lambda x: x['created_at'], reverse=True)
        
        # 5. Paginate manually
        total = len(combined)
        start = (page - 1) * page_size
        end = start + page_size
        items = combined[start:end]
        
        return jsonify({
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total // page_size) + (1 if total % page_size > 0 else 0)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@pedidos_bp.route('/api/admin/pedidos/<int:pedido_id>', methods=['GET'])
@jwt_required()
def get_pedido_detalle(pedido_id):
    try:
        pedido = Pedido.query.get_or_404(pedido_id)
        return jsonify(pedido.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@pedidos_bp.route('/api/admin/pedidos/<int:pedido_id>', methods=['PATCH', 'PUT'])
@jwt_required()
def update_pedido_estado(pedido_id):
    try:
        pedido = Pedido.query.get_or_404(pedido_id)
        data = request.get_json()
        if 'estado' in data:
            pedido.estado = data['estado']
        db.session.commit()
        invalidate_cache(pattern='estadisticas')
        return jsonify(pedido.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@pedidos_bp.route('/api/admin/pedidos/pendientes', methods=['GET'])
@jwt_required()
def get_pedidos_pendientes():
    try:
        pedidos = Pedido.query.filter_by(aprobado=False, estado='pendiente_aprobacion').order_by(Pedido.created_at.desc()).all()
        return jsonify([p.to_dict() for p in pedidos]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@pedidos_bp.route('/api/admin/pedidos/<int:pedido_id>/aprobar', methods=['POST'])
@jwt_required()
def aprobar_pedido(pedido_id):
    try:
        pedido = Pedido.query.get_or_404(pedido_id)
        if pedido.aprobado:
            return jsonify({'error': 'El pedido ya está aprobado'}), 400
        if pedido.fecha_expiracion and pedido.fecha_expiracion < datetime.utcnow():
            return jsonify({'error': 'El pedido ha expirado y no puede ser aprobado'}), 400

        for item in pedido.items:
            stock_talle = StockTalle.query.filter_by(producto_id=item.producto_id, talle_id=item.talle_id).first()
            if not stock_talle or stock_talle.cantidad < item.cantidad:
                producto = Producto.query.get(item.producto_id)
                talle = Talle.query.get(item.talle_id)
                return jsonify({'error': f'Stock insuficiente para {producto.nombre} talle {talle.nombre}'}), 400

        admin_identity = get_jwt_identity()
        admin = Admin.query.filter_by(username=admin_identity).first()

        pedido.aprobado = True
        pedido.fecha_aprobacion = datetime.utcnow()
        pedido.admin_aprobador_id = admin.id if admin else None
        pedido.estado = 'confirmado'

        for item in pedido.items:
            stock_talle = StockTalle.query.filter_by(producto_id=item.producto_id, talle_id=item.talle_id).first()
            if stock_talle:
                stock_talle.reducir_stock(item.cantidad)
            producto = Producto.query.get(item.producto_id)
            if producto:
                producto.ventas_count = (producto.ventas_count or 0) + item.cantidad

        db.session.commit()
        invalidate_cache(pattern='estadisticas')
        invalidate_cache(pattern='productos')

        try:
            from services.notification_service import NotificationService
            NotificationService.send_order_approved_email(pedido)
        except Exception as notif_err:
            print(f"Error enviando notificacion aprobacion: {notif_err}")

        return jsonify({'message': 'Pedido aprobado exitosamente', 'pedido': pedido.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@pedidos_bp.route('/api/admin/pedidos/<int:pedido_id>/notas', methods=['GET', 'POST'])
@jwt_required()
def manage_notas_pedido(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    if request.method == 'GET':
        notas = NotaPedido.query.filter_by(pedido_id=pedido_id).order_by(NotaPedido.created_at.desc()).all()
        return jsonify([n.to_dict() for n in notas]), 200
    data = request.get_json()
    admin_id = get_jwt_identity()
    admin = Admin.query.get(int(admin_id))
    if not admin:
        return jsonify({'error': 'Admin no encontrado'}), 404
    nota = NotaPedido(pedido_id=pedido_id, admin_id=admin.id, contenido=data.get('contenido', ''))
    db.session.add(nota)
    db.session.commit()
    return jsonify(nota.to_dict()), 201


@pedidos_bp.route('/api/admin/notas/<int:nota_id>', methods=['DELETE'])
@jwt_required()
def delete_nota(nota_id):
    nota = NotaPedido.query.get_or_404(nota_id)
    db.session.delete(nota)
    db.session.commit()
    return jsonify({'message': 'Nota eliminada'}), 200
