from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, decode_token
from extensions import limiter
from models import Cliente, Pedido, db
from services.notification_service import NotificationService
import re
import logging
import random
import time
from datetime import timedelta

logger = logging.getLogger(__name__)
clients_bp = Blueprint('clients', __name__)

def verify_recaptcha(token):
    secret_key = current_app.config.get('RECAPTCHA_SECRET_KEY', '6LfgSlssAAAAAFWj1hXPYvUlp3xK3x6bU2pvYZXI') # CLAVE SK PRODUCCION
    if not secret_key or not token:
        # Si no hay key configurada, bypass (para dev) o error log
        print("DEBUG RECAPTCHA: No secret key or token provided", flush=True)
        return True # Fail open in dev if needed, or False
        
    try:
        import requests
        resp = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={
                'secret': secret_key,
                'response': token
            },
            timeout=5
        )
        result = resp.json()
        print(f"DEBUG RECAPTCHA: Verify result: {result}", flush=True)
        return result.get('success', False)
    except Exception as e:
        print(f"DEBUG RECAPTCHA: Error verifying: {e}", flush=True)
        return False

@clients_bp.route('/api/clientes', methods=['POST'])
@limiter.limit("50 per hour")
def registrar_cliente():
    try:
        data = request.json
        print(f"DEBUG CLIENTES: Recibida solicitud de registro para {data.get('email')}", flush=True)
        
        # Validar captcha (OBLIGATORIO)
        captcha_token = data.get('recaptcha_token')
        if not captcha_token:
            return jsonify({'error': 'Falta el captcha'}), 400
            
        if not verify_recaptcha(captcha_token):
             return jsonify({'error': 'Captcha inválido. Por favor intenta de nuevo.'}), 400

        if not data.get('nombre') or not data.get('email') or not data.get('password') or not data.get('metodo_verificacion'):
            return jsonify({'error': 'Faltan campos requeridos (incluyendo método de verificación)'}), 400
        
        password = data['password']
        if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'\d', password):
            return jsonify({'error': 'La contraseña no cumple los requisitos de seguridad'}), 400
        
        cliente = Cliente.query.filter_by(email=data['email']).first()
        
        if cliente:
            if cliente.telefono_verificado:
                return jsonify({'error': 'Email ya registrado'}), 400
            else:
                # Si existe pero no está verificado, actualizamos sus datos y mandamos código nuevo
                print(f"DEBUG CLIENTES: Re-registro para cuenta no verificada: {data['email']}", flush=True)
                cliente.nombre = data['nombre']
                cliente.telefono = data.get('telefono')
                cliente.metodo_verificacion = 'email'
                cliente.acepta_newsletter = data.get('acepta_newsletter', True)
        else:
            # Crear nuevo cliente
            cliente = Cliente(
                nombre=data['nombre'],
                email=data['email'],
                telefono=data.get('telefono'),
                metodo_verificacion='email',
                acepta_newsletter=data.get('acepta_newsletter', True)
            )
            db.session.add(cliente)
            
        cliente.set_password(password)
        cliente.codigo_verificacion = str(random.randint(100000, 999999))
        db.session.commit()
        
        # Enviar código de forma asíncrona para no demorar la respuesta
        try:
            from threading import Thread
            from flask import current_app
            def send_async_code(app, cliente_id, codigo, metodo):
                with app.app_context():
                    from models import Cliente
                    c = Cliente.query.get(cliente_id)
                    if c:
                        NotificationService.send_verification_code(c, codigo, metodo)

            Thread(target=send_async_code, args=(current_app._get_current_object(), cliente.id, cliente.codigo_verificacion, cliente.metodo_verificacion)).start()
        except Exception as thread_err:
            print(f"DEBUG CLIENTES: Error al lanzar thread de notificación: {thread_err}", flush=True)

        logger.info(f"🆕 REGISTRO OK: {cliente.email} - Verif: {cliente.metodo_verificacion}")
        return jsonify(cliente.to_dict()), 201
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"DEBUG CLIENTES: ERROR CRÍTICO en registrar_cliente: {str(e)}\n{error_trace}", flush=True)
        return jsonify({'error': f'Ocurrió un error en el servidor. Por favor intenta más tarde.'}), 500

@clients_bp.route('/api/clientes/login', methods=['POST'])
@limiter.limit("10 per minute")
def login_cliente():
    data = request.json
    
    # Validar captcha (opcional por ahora)
    # Validar captcha (OBLIGATORIO)
    captcha_token = data.get('recaptcha_token')
    if not captcha_token:
        return jsonify({'error': 'Falta el captcha'}), 400

    if not verify_recaptcha(captcha_token):
       return jsonify({'error': 'Captcha inválido'}), 400

    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email y contraseña requeridos'}), 400
    
    cliente = Cliente.query.filter_by(email=email).first()
    if cliente and cliente.check_password(password):
        access_token = create_access_token(identity=str(cliente.id))
        return jsonify({'access_token': access_token, 'cliente': cliente.to_dict()}), 200
    
    return jsonify({'error': 'Credenciales inválidas'}), 401

@clients_bp.route('/api/clientes/verify-code', methods=['POST'])
@limiter.limit("5 per minute")
def verificar_codigo():
    data = request.json
    email = data.get('email')
    codigo_recibido = str(data.get('codigo'))
    
    cliente = Cliente.query.filter_by(email=email).first()
    
    if not cliente:
        print(f"DEBUG VERIFICACION: Email {email} no encontrado", flush=True)
        return jsonify({'error': 'Email no encontrado'}), 404
        
    print(f"DEBUG VERIFICACION: Evaluando {email}. Recibido: [{codigo_recibido}], Esperado: [{cliente.codigo_verificacion}]", flush=True)
    
    if cliente.codigo_verificacion == codigo_recibido:
        cliente.telefono_verificado = True
        cliente.codigo_verificacion = None
        db.session.commit()
        print(f"DEBUG VERIFICACION: {email} verificado con éxito", flush=True)
        
        # Generar token para auto-login
        access_token = create_access_token(identity=str(cliente.id))
        return jsonify({
            'message': 'Verificado',
            'access_token': access_token,
            'cliente': cliente.to_dict()
        }), 200
        
    print(f"DEBUG VERIFICACION: {email} falló. Código incorrecto.", flush=True)
    return jsonify({'error': 'Código inválido'}), 400

@clients_bp.route('/api/clientes/resend-code', methods=['POST'])
@limiter.limit("3 per minute")
def reenviar_codigo():
    data = request.json
    email = data.get('email')
    cliente = Cliente.query.filter_by(email=email).first()
    
    if not cliente:
        return jsonify({'error': 'Email no encontrado'}), 404
    
    # Generar nuevo código
    cliente.codigo_verificacion = str(random.randint(100000, 999999))
    db.session.commit()
    
    # Enviar de forma asíncrona
    from threading import Thread
    from flask import current_app
    def send_async_code(app, cliente_id, codigo, metodo):
        with app.app_context():
            from models import Cliente
            c = Cliente.query.get(cliente_id)
            if c:
                NotificationService.send_verification_code(c, codigo, metodo)

    Thread(target=send_async_code, args=(current_app._get_current_object(), cliente.id, cliente.codigo_verificacion, cliente.metodo_verificacion)).start()
    
    return jsonify({'message': 'Código reenviado'}), 200

@clients_bp.route('/api/auth/forgot-password', methods=['POST'])
@limiter.limit("3 per hour")
def forgot_password():
    email = request.json.get('email')
    cliente = Cliente.query.filter_by(email=email).first()
    if cliente:
        token = create_access_token(identity=str(cliente.id), additional_claims={'purpose': 'password_reset'}, expires_delta=timedelta(hours=1))
        NotificationService.send_password_reset_email(cliente.email, token, cliente.nombre)
    return jsonify({'message': 'Si el email existe, se ha enviado un enlace'}), 200

@clients_bp.route('/api/auth/reset-password', methods=['POST'])
@limiter.limit("5 per hour")
def reset_password():
    data = request.json
    try:
        decoded = decode_token(data.get('token'))
        if decoded.get('purpose') != 'password_reset': raise Exception("Invalid token purpose")
        cliente = Cliente.query.get(decoded['sub'])
        if cliente:
            cliente.set_password(data.get('password'))
            db.session.commit()
            return jsonify({'message': 'Contraseña actualizada'}), 200
    except:
        pass
    return jsonify({'error': 'Token inválido o expirado'}), 400

@clients_bp.route('/api/clientes/verify', methods=['GET'])
@jwt_required()
def verify_token_cliente():
    """Verificar token JWT para cliente"""
    cliente_id = get_jwt_identity()
    cliente = Cliente.query.get(cliente_id)
    if not cliente:
        return jsonify({'error': 'Cliente no encontrado'}), 404
        
    return jsonify({
        'cliente': cliente.to_dict()
    }), 200

@clients_bp.route('/api/clientes/me', methods=['PUT'])
@jwt_required()
def update_profile():
    cliente_id = get_jwt_identity()
    cliente = Cliente.query.get(cliente_id)
    if not cliente:
        return jsonify({'error': 'Cliente no encontrado'}), 404
        
    data = request.json
    if 'nombre' in data:
        cliente.nombre = data['nombre']
    if 'telefono' in data:
        cliente.telefono = data['telefono']
    
    db.session.commit()
    return jsonify(cliente.to_dict()), 200

@clients_bp.route('/api/clientes/change-password', methods=['POST'])
@jwt_required()
def change_password():
    cliente_id = get_jwt_identity()
    cliente = Cliente.query.get(cliente_id)
    if not cliente:
        return jsonify({'error': 'Cliente no encontrado'}), 404
        
    data = request.json
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({'error': 'Faltan datos'}), 400
        
    if not cliente.check_password(old_password):
        return jsonify({'error': 'Contraseña actual incorrecta'}), 400
        
    if len(new_password) < 8:
         return jsonify({'error': 'La nueva contraseña debe tener al menos 8 caracteres'}), 400
         
    cliente.set_password(new_password)
    db.session.commit()
    
    return jsonify({'message': 'Contraseña actualizada correctamente'}), 200

@clients_bp.route('/api/clientes/me/orders', methods=['GET'])
@jwt_required()
def get_my_orders():
    cliente_id = get_jwt_identity()
    cliente = Cliente.query.get(cliente_id)
    if not cliente:
        return jsonify({'error': 'Cliente no encontrado'}), 404
        
    # Buscar pedidos por email del cliente (case insensitive y sin espacios)
    # DEBUG: Log para ver qué está pasando
    print(f"DEBUG: Buscando pedidos para usuario ID {cliente.id} con email [{cliente.email}] y telefono [{cliente.telefono}]", flush=True)
    
    # Lista para acumular resultados únicos
    pedidos_map = {}

    # 1. Búsqueda por EMAIL
    search_email = cliente.email.strip().lower()
    
    # Intentar búsqueda exacta primero
    pedidos_email_exact = Pedido.query.filter(Pedido.cliente_email == search_email).all()
    for p in pedidos_email_exact: pedidos_map[p.id] = p
    
    # Búsqueda flexible email
    pedidos_email_like = Pedido.query.filter(Pedido.cliente_email.ilike(f"%{search_email}%")).all()
    for p in pedidos_email_like: pedidos_map[p.id] = p

    # 2. Búsqueda por TELÉFONO (si el cliente tiene)
    if cliente.telefono:
        # Limpiar teléfono cliente (dejar solo dígitos)
        clean_phone = "".join(filter(str.isdigit, str(cliente.telefono)))
        
        # Usar los últimos 7 dígitos para máxima compatibilidad en Argentina
        # (ignora prefijos 54, 9, 0, y el infame 15)
        # 5493584171716 -> 4171716
        # 0358154171716 -> 4171716
        
        search_term = clean_phone
        if len(clean_phone) > 7:
            search_term = clean_phone[-7:]
            
        if len(search_term) >= 6: # Mínimo de seguridad
            print(f"DEBUG: Intentando búsqueda por teléfono. Term: {search_term} (Original: {clean_phone})", flush=True)
            pedidos_fono = Pedido.query.filter(Pedido.cliente_telefono.ilike(f"%{search_term}%")).all()
            
            for p in pedidos_fono:
                pedidos_map[p.id] = p
                
    # Convertir a lista y ordenar
    pedidos_finales = list(pedidos_map.values())
    pedidos_finales.sort(key=lambda x: x.created_at, reverse=True)

    print(f"DEBUG: Se encontraron {len(pedidos_finales)} pedidos en total para {search_email}", flush=True)

    return jsonify([p.to_dict() for p in pedidos_finales]), 200

@clients_bp.route('/api/clientes/me/orders/<int:pedido_id>', methods=['DELETE'])
@jwt_required()
def delete_my_order(pedido_id):
    cliente_id = get_jwt_identity()
    cliente = Cliente.query.get(cliente_id)
    if not cliente:
        return jsonify({'error': 'Cliente no encontrado'}), 404

    pedido = Pedido.query.get_or_404(pedido_id)

    # Security check: Ensure order belongs to this client or matches email/phone
    # Simplest check: Matches exact email used in account
    is_owner = False
    
    if pedido.cliente_email and pedido.cliente_email.lower().strip() == cliente.email.lower().strip():
        is_owner = True
    elif cliente.telefono:
         # Simplified phone check similar to get_orders
         clean_user_phone = "".join(filter(str.isdigit, str(cliente.telefono)))
         clean_order_phone = "".join(filter(str.isdigit, str(pedido.cliente_telefono or '')))
         if len(clean_user_phone) > 6 and clean_user_phone in clean_order_phone:
             is_owner = True

    if not is_owner:
        print(f"DEBUG DELETE: ID {pedido_id} - Forbidden (User {cliente.id} vs Order Owner)", flush=True)
        return jsonify({'error': 'No tienes permiso para eliminar este pedido'}), 403

    try:
        # HARD DELETE as requested "que no aparezca"
        print(f"DEBUG DELETE: Attempting to delete order {pedido_id}...", flush=True)
        
        # 1. Manually delete NotaPedido items if any (ORM cascade missing)
        from models import NotaPedido
        try:
            NotaPedido.query.filter_by(pedido_id=pedido.id).delete()
        except Exception as e:
            print(f"DEBUG DELETE: Error deleting notes: {e}", flush=True)

        # 2. Check other non-cascaded relationships?
        # Items and Entvio have cascade='all, delete-orphan' in Pedido model.
        
        db.session.delete(pedido)
        db.session.commit()
        print(f"DEBUG DELETE: Success {pedido_id}", flush=True)
        return jsonify({'message': 'Pedido eliminado correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        logger.error(f"Error deleting order {pedido_id}: {e}")
        return jsonify({'error': f'Error al eliminar el pedido: {str(e)}'}), 500

@clients_bp.route('/api/newsletter/subscribe', methods=['POST'])
@limiter.limit("20 per hour")
def subscribe_newsletter():
    try:
        data = request.json
        email = data.get('email')
        nombre = data.get('nombre')
        
        if not email:
            return jsonify({'error': 'El email es requerido'}), 400
            
        cliente = Cliente.query.filter_by(email=email).first()
        
        if cliente:
            # Cliente existente, actualizamos suscripción
            cliente.acepta_newsletter = True
            if nombre and not cliente.nombre: # Actualizar nombre si no tenía
                cliente.nombre = nombre
            db.session.commit()
            message = '¡Gracias por suscribirte nuevamente! Te mantendremos informado.'
        else:
            # Nuevo cliente solo para newsletter
            cliente = Cliente(
                nombre=nombre if nombre else 'Suscriptor',
                email=email,
                acepta_newsletter=True,
                metodo_verificacion='email', # Asumimos verificado o pendiente, pero para newsletter no bloqueamos
                password_hash=None # Sin password
            )
            db.session.add(cliente)
            db.session.commit()
            message = '¡Gracias por suscribirte! Recibirás nuestras novedades pronto.'
            
        # Intentar enviar email de bienvenida (opcional, si existe método)
        try:
            # Por ahora solo logueamos, idealmente NotificationService.send_welcome_newsletter(cliente)
            logger.info(f"📧 Newsletter suscripción: {email}")
        except:
            pass
            
        return jsonify({'message': message}), 200
        
    except Exception as e:
        logger.error(f"Error en newsletter subscribe: {e}")
        return jsonify({'error': 'Ocurrió un error al procesar la suscripción'}), 500

