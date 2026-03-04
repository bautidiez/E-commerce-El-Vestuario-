"""
Blueprint de estadísticas del panel admin.
Rutas: GET /api/admin/estadisticas, GET /api/admin/estadisticas/ventas
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from cache_utils import cache
from services.admin_service import AdminService
from datetime import datetime

estadisticas_bp = Blueprint('admin_estadisticas', __name__)


@estadisticas_bp.route('/api/admin/estadisticas', methods=['GET'])
@jwt_required()
def get_estadisticas():
    cache_key = "estadisticas:general_v3"
    cached_result = cache.get(cache_key)
    if cached_result:
        return jsonify(cached_result), 200
    try:
        stats = AdminService.get_dashboard_stats()
        cache.set(cache_key, stats, ttl_seconds=300)
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@estadisticas_bp.route('/api/admin/estadisticas/ventas', methods=['GET'])
@jwt_required()
def get_estadisticas_ventas():
    periodo = request.args.get('periodo', 'dia')
    fecha_ref = request.args.get('fecha_referencia')
    semana_offset = int(request.args.get('semana_offset', 0))
    anio = request.args.get('anio')
    if anio:
        anio = int(anio)

    cache_key = f"estadisticas_ventas:{periodo}:{fecha_ref}:{semana_offset}:{anio}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return jsonify(cached_result), 200

    try:
        dt_ref = None
        if fecha_ref:
            dt_ref = datetime.strptime(fecha_ref, '%Y-%m-%d')
        stats = AdminService.get_sales_stats(periodo, dt_ref, semana_offset, anio)
        cache.set(cache_key, stats, ttl_seconds=300)
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
