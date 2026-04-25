from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from firebase_admin import auth as firebase_auth
from models import Cliente, db
import logging

logger = logging.getLogger(__name__)
google_auth_bp = Blueprint('google_auth', __name__)

@google_auth_bp.route('/api/auth/google', methods=['POST'])
def google_login():
    """
    Recibe un ID Token de Firebase desde el frontend, 
    lo verifica y autentica al cliente (creándolo si no existe).
    """
    data = request.get_json()
    token = data.get('idToken')

    if not token:
        return jsonify({'error': 'Token requerido'}), 400

    try:
        # Verificar el token con Firebase Admin SDK
        decoded_token = firebase_auth.verify_id_token(token)
        google_id = decoded_token['uid']
        email = decoded_token.get('email')
        nombre = decoded_token.get('name', 'Usuario Google')
        imagen_url = decoded_token.get('picture')

        if not email:
            return jsonify({'error': 'La cuenta de Google debe tener un email asociado'}), 400

        # Buscar si el cliente ya existe por google_id
        cliente = Cliente.query.filter_by(google_id=google_id).first()

        # Si no existe por google_id, buscar por email (para vincular cuentas)
        if not cliente:
            cliente = Cliente.query.filter(db.func.lower(Cliente.email) == db.func.lower(email)).first()
            if cliente:
                # Vincular cuenta existente con Google
                cliente.google_id = google_id
                if not cliente.imagen_url:
                    cliente.imagen_url = imagen_url
                db.session.commit()
                logger.info(f"Cuenta vinculada con Google: {email}")

        # Si aún no existe, crear nuevo cliente
        if not cliente:
            cliente = Cliente(
                nombre=nombre,
                email=email,
                google_id=google_id,
                imagen_url=imagen_url,
                acepta_newsletter=True # Por defecto
            )
            db.session.add(cliente)
            db.session.commit()
            logger.info(f"Nuevo cliente creado vía Google: {email}")

        # Generar JWT propio de nuestra API
        access_token = create_access_token(identity=str(cliente.id))

        return jsonify({
            'access_token': access_token,
            'user_type': 'cliente',
            'cliente': cliente.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error en Google Login: {str(e)}")
        return jsonify({'error': 'Error de autenticación con Google', 'details': str(e)}), 401
