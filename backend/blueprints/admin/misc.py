"""
Blueprint de talles, colores, newsletter y utilidades DB (admin).
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from models import Talle, Color, Cliente, db

misc_bp = Blueprint('admin_misc', __name__)


# ── Talles ─────────────────────────────────────────────────────────────────────

@misc_bp.route('/api/admin/talles', methods=['POST'])
@jwt_required()
def create_talle():
    data = request.get_json()
    try:
        talle = Talle(nombre=data['nombre'], orden=data.get('orden', 0))
        db.session.add(talle)
        db.session.commit()
        return jsonify(talle.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@misc_bp.route('/api/admin/talles/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_talle(id):
    talle = Talle.query.get_or_404(id)
    try:
        db.session.delete(talle)
        db.session.commit()
        return jsonify({'message': 'Talle eliminado'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ── Colores ───────────────────────────────────────────────────────────────────

@misc_bp.route('/api/admin/colores', methods=['POST'])
@jwt_required()
def create_color():
    data = request.get_json()
    try:
        color = Color(nombre=data['nombre'], codigo_hex=data.get('codigo_hex'))
        db.session.add(color)
        db.session.commit()
        return jsonify(color.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ── DB Utils ──────────────────────────────────────────────────────────────────

@misc_bp.route('/api/admin/db/fix-sequences', methods=['POST'])
@jwt_required()
def fix_db_sequences_route():
    """Sincroniza las secuencias de las tablas con su ID máximo (PostgreSQL)"""
    try:
        from sqlalchemy import text
        tablas = ['categorias', 'productos', 'pedidos', 'clientes', 'admins', 'talles', 'colores', 'stock_talles', 'metodos_pago', 'promociones']
        detalles = []
        is_postgres = 'postgresql' in current_app.config.get('SQLALCHEMY_DATABASE_URI', '').lower()
        if not is_postgres:
            return jsonify({'message': 'No es PostgreSQL, no se requiere fix de secuencias'}), 200
        for tabla in tablas:
            try:
                db.session.execute(text(f"SELECT setval('{tabla}_id_seq', COALESCE((SELECT MAX(id) FROM {tabla}), 1))"))
                detalles.append(f"✓ {tabla}")
            except Exception as te:
                detalles.append(f"✗ {tabla}: {str(te)}")
        db.session.commit()
        return jsonify({'message': 'Sincronización completada', 'detalles': detalles}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ── Newsletter ────────────────────────────────────────────────────────────────

@misc_bp.route('/api/admin/newsletter/send', methods=['POST'])
@jwt_required()
def send_marketing_newsletter():
    try:
        from models import NewsletterHistory

        data = request.get_json()
        subject = data.get('subject')
        content = data.get('content')
        test_email = data.get('test_email')
        if not subject or not content:
            return jsonify({'error': 'Asunto y contenido son requeridos'}), 400

        recipients = []
        if not test_email:
            clientes = Cliente.query.filter_by(acepta_newsletter=True).all()
            recipients = [{'email': c.email, 'nombre': c.nombre} for c in clientes]
            if not recipients:
                return jsonify({'error': 'No hay suscriptores para enviar'}), 400
        else:
            recipients = [{'email': test_email, 'nombre': 'Admin Test'}]

        from services.notification_service import NotificationService
        sent_count = NotificationService.send_newsletter(subject, content, recipients, test_email)

        # Guardar en historial (solo si no es un envío de prueba)
        if not test_email:
            try:
                historial = NewsletterHistory(
                    asunto=subject,
                    contenido=content,
                    sent_count=sent_count
                )
                db.session.add(historial)
                db.session.commit()
            except Exception as hist_err:
                print(f"Error guardando historial newsletter: {hist_err}")
                db.session.rollback()

        return jsonify({'message': 'Newsletter procesado', 'sent_count': sent_count, 'total_targets': len(recipients)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@misc_bp.route('/api/admin/newsletter/history', methods=['GET'])
@jwt_required()
def get_newsletter_history():
    try:
        from models import NewsletterHistory
        history = NewsletterHistory.query.order_by(NewsletterHistory.sent_at.desc()).limit(30).all()
        return jsonify([h.to_dict() for h in history]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@misc_bp.route('/api/admin/newsletter/scheduled', methods=['GET'])
@jwt_required()
def get_scheduled_newsletters():
    try:
        from models import ScheduledNewsletter
        scheduled = ScheduledNewsletter.query.order_by(ScheduledNewsletter.created_at.desc()).all()
        return jsonify([s.to_dict() for s in scheduled]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@misc_bp.route('/api/admin/newsletter/schedule', methods=['POST'])
@jwt_required()
def schedule_newsletter():
    try:
        from models import ScheduledNewsletter, db
        from datetime import datetime

        data = request.get_json()
        subject = data.get('subject')
        content = data.get('content')
        tipo = data.get('tipo', 'unica') # 'unica', 'semanal', 'mensual'
        
        if not subject or not content:
            return jsonify({'error': 'Asunto y contenido son requeridos'}), 400

        scheduled = ScheduledNewsletter(
            asunto=subject,
            contenido=content,
            tipo=tipo,
            hora_envio=data.get('hora_envio')
        )

        if tipo == 'unica':
            # Formato esperado: "YYYY-MM-DDTHH:MM"
            if data.get('scheduled_at'):
                scheduled.scheduled_at = datetime.fromisoformat(data['scheduled_at'].replace('Z', ''))
        
        elif tipo == 'semanal':
            scheduled.dia_semana = data.get('dia_semana') # 0-6
        
        elif tipo == 'mensual':
            scheduled.dia_semana = data.get('dia_semana') # 0-6
            scheduled.posicion_mes = data.get('posicion_mes') # 1-5

        db.session.add(scheduled)
        db.session.commit()
        return jsonify(scheduled.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@misc_bp.route('/api/admin/newsletter/scheduled/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_scheduled_newsletter(id):
    try:
        from models import ScheduledNewsletter, db
        item = ScheduledNewsletter.query.get_or_404(id)
        db.session.delete(item)
        db.session.commit()
        return jsonify({'message': 'Programación eliminada'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
