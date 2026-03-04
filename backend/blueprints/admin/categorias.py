"""
Blueprint de gestión de categorías (admin).
Rutas: /api/admin/categorias
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from cache_utils import invalidate_cache
from models import Categoria, db
import logging

logger = logging.getLogger(__name__)
categorias_bp = Blueprint('admin_categorias', __name__)


@categorias_bp.route('/api/admin/categorias', methods=['POST'])
@jwt_required()
def create_categoria():
    data = request.get_json()
    if not data.get('nombre'):
        return jsonify({'error': 'Nombre es requerido'}), 400

    padre_id = data.get('categoria_padre_id')
    if padre_id in ('', 'null', 0, None):
        padre_id = None
    else:
        try:
            padre_id = int(padre_id)
        except (ValueError, TypeError):
            padre_id = None

    max_retries = 2
    for attempt in range(max_retries):
        try:
            categoria = Categoria(
                nombre=data['nombre'],
                descripcion=data.get('descripcion', ''),
                imagen=data.get('imagen'),
                categoria_padre_id=padre_id,
                orden=int(data.get('orden', 0)),
                activa=data.get('activa', True),
                slug=data.get('slug')
            )
            db.session.add(categoria)
            if 'subcategorias_nuevas' in data:
                for sub_data in data['subcategorias_nuevas']:
                    sub_cat = Categoria(
                        nombre=sub_data['nombre'],
                        descripcion=sub_data.get('descripcion', ''),
                        categoria_padre=categoria,
                        orden=int(sub_data.get('orden', 0)),
                        activa=sub_data.get('activa', True)
                    )
                    db.session.add(sub_cat)
            db.session.commit()
            invalidate_cache(pattern='categorias')
            return jsonify(categoria.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            err_str = str(e)
            if attempt < max_retries - 1 and ('UniqueViolation' in err_str or 'duplicate key' in err_str):
                try:
                    from sqlalchemy import text
                    db.session.execute(text("SELECT setval('categorias_id_seq', COALESCE((SELECT MAX(id) FROM categorias), 1))"))
                    db.session.commit()
                    continue
                except:
                    pass
            return jsonify({'error': err_str}), 500


@categorias_bp.route('/api/admin/categorias/<int:id>', methods=['PUT', 'DELETE'])
@jwt_required()
def manage_category(id):
    categoria = Categoria.query.get_or_404(id)
    if request.method == 'DELETE':
        force = request.args.get('force', 'false') == 'true'
        try:
            if not force and categoria.productos:
                return jsonify({'error': 'La categoría tiene productos asociados. Use force=true para borrar.'}), 400
            db.session.delete(categoria)
            db.session.commit()
            invalidate_cache(pattern='categorias')
            return jsonify({'message': 'Categoría eliminada'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    data = request.get_json()
    try:
        if 'nombre' in data: categoria.nombre = data['nombre']
        if 'descripcion' in data: categoria.descripcion = data['descripcion']
        if 'imagen' in data: categoria.imagen = data['imagen']
        if 'categoria_padre_id' in data:
            padre_id = data['categoria_padre_id']
            if padre_id in ('', 'null', 0, None):
                categoria.categoria_padre_id = None
            else:
                try:
                    categoria.categoria_padre_id = int(padre_id)
                except (ValueError, TypeError):
                    categoria.categoria_padre_id = None
        if 'orden' in data: categoria.orden = int(data['orden'])
        if 'activa' in data: categoria.activa = data['activa']
        if 'slug' in data: categoria.slug = data['slug']
        if 'subcategorias_nuevas' in data:
            for sub_data in data['subcategorias_nuevas']:
                if sub_data.get('nombre'):
                    sub_cat = Categoria(
                        nombre=sub_data['nombre'],
                        descripcion=sub_data.get('descripcion', ''),
                        categoria_padre=categoria,
                        orden=int(sub_data.get('orden', 0)),
                        activa=sub_data.get('activa', True)
                    )
                    db.session.add(sub_cat)
        db.session.commit()
        invalidate_cache(pattern='categorias')
        invalidate_cache(pattern='productos')
        return jsonify(categoria.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
