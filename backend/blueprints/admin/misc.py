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
        from datetime import datetime, timedelta
        import json

        if not test_email:
            # Obtener todos los suscriptores ordenados por ID desc (últimos registrados primero)
            clientes = Cliente.query.filter_by(acepta_newsletter=True).order_by(Cliente.id.desc()).all()
            all_recipients = [{'email': c.email, 'nombre': c.nombre} for c in clientes]
            
            if not all_recipients:
                return jsonify({'error': 'No hay suscriptores para enviar'}), 400

            # Si son menos de 300, enviar todo ahora
            if len(all_recipients) <= 300:
                sent_count = NotificationService.send_newsletter(subject, content, all_recipients, test_email)
                
                # Guardar en historial
                historial = NewsletterHistory(asunto=subject, contenido=content, sent_count=sent_count)
                db.session.add(historial)
                db.session.commit()
                
                return jsonify({'message': 'Newsletter enviado exitosamente', 'sent_count': sent_count}), 200
            
            else:
                # LÓGICA DE GOTEO (Drip) - Más de 300 destinatarios
                # Grupo 1: Primeros 300 (enviar ahora)
                grupo_ahora = all_recipients[:300]
                restantes = all_recipients[300:]
                
                sent_count = NotificationService.send_newsletter(subject, content, grupo_ahora)
                
                # Guardar primer envío en historial
                historial = NewsletterHistory(asunto=subject, contenido=f"[Grupo 1/Gotéo] {content[:50]}...", sent_count=sent_count)
                db.session.add(historial)
                
                # Programar el resto en bloques de 300 para los días siguientes
                from models import ScheduledNewsletter
                chunk_size = 300
                dias_offset = 1
                
                for i in range(0, len(restantes), chunk_size):
                    chunk = restantes[i:i + chunk_size]
                    proximo_envio = datetime.utcnow() + timedelta(days=dias_offset)
                    
                    programado = ScheduledNewsletter(
                        asunto=f"(Continuación) {subject}",
                        contenido=content,
                        tipo='unica',
                        scheduled_at=proximo_envio,
                        destinatarios=json.dumps(chunk),
                        activa=True
                    )
                    db.session.add(programado)
                    dias_offset += 1
                
                db.session.commit()
                return jsonify({
                    'message': f'Se enviaron 300 emails ahora. Los restantes {len(restantes)} se programaron automáticamente en bloques diarios para respetar el límite de 300/día.',
                    'sent_now': sent_count,
                    'total_scheduled': len(restantes)
                }), 200

        else:
            # Envío de prueba (siempre ahora)
            recipients = [{'email': test_email, 'nombre': 'Admin Test'}]
            sent_count = NotificationService.send_newsletter(subject, content, recipients, test_email)
            return jsonify({'message': 'Newsletter de prueba enviado', 'sent_count': sent_count}), 200

    except Exception as e:
        db.session.rollback()
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


@misc_bp.route('/api/admin/newsletter/stats', methods=['GET'])
@jwt_required()
def get_newsletter_stats():
    """Retorna estadísticas de usuarios registrados únicos"""
    try:
        from models import Cliente
        # Intentar varias formas de conteo por si acaso
        count_orm = Cliente.query.count()
        
        # Conteo crudo por si el ORM tiene algún filtro global (poco probable pero posible)
        from sqlalchemy import text
        result = db.session.execute(text("SELECT COUNT(*) FROM clientes")).fetchone()
        count_raw = result[0] if result else 0
        
        # Usar el mayor por las dudas, o el que funcione
        final_count = max(count_orm, count_raw)
        
        print(f"DEBUG STATS: ORM={count_orm}, RAW={count_raw}")
        
        return jsonify({
            'total_subscribers': final_count,
            'debug_info': {
                'orm': count_orm,
                'raw': count_raw
            }
        }), 200
    except Exception as e:
        print(f"ERROR IN STATS: {str(e)}")
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
