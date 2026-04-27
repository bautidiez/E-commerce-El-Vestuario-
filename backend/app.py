from flask import Flask, jsonify
import sys

# Evitar ejecución directa para prevenir errores de importación circular
if __name__ == '__main__':
    print("\n\nERROR CRÍTICO: No ejecutes este archivo directamente.")
    print("POR FAVOR EJECUTA: python run.py\n\n")
    sys.exit(1)

from datetime import timedelta
from dotenv import load_dotenv
import os
import time
import logging
from extensions import jwt, mail, compress, cors, limiter
import firebase_admin
from firebase_admin import credentials

# Cargar variables de entorno
load_dotenv()

# Inicializar Flask
app = Flask(__name__)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'tu-clave-secreta-cambiar-en-produccion')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///instance/elvestuario.db')
print(f"DEBUG: Using database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configurar pool de conexiones para mejor rendimiento
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'max_overflow': 20
}

# Inicializar db desde models
from models import db
db.init_app(app)

# Habilitar modo WAL solo si se usa SQLite
from sqlalchemy import event, text, or_
with app.app_context():
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
        @event.listens_for(db.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-cambiar-en-produccion')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Crear directorio de uploads si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configuracion de Email
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False') == 'True'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '').replace(' ', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

# Configuración de Flask-Compress
app.config['COMPRESS_MIMETYPES'] = [
    'text/html',
    'text/css',
    'text/xml',
    'application/json',
    'application/javascript',
    'text/javascript'
]
app.config['COMPRESS_LEVEL'] = 6  # Nivel de compresión (1-9, 6 es balance entre velocidad y tamaño)
app.config['COMPRESS_MIN_SIZE'] = 500  # Comprimir respuestas > 500 bytes

# Inicializar extensiones
# Inicializar extensiones
jwt.init_app(app)
mail.init_app(app)
cors.init_app(app)
compress.init_app(app)
limiter.init_app(app)

# Inicializar Firebase
firebase_creds_path = os.environ.get('FIREBASE_CREDENTIALS_PATH', 'backend/firebase-service-account.json')
if os.path.exists(firebase_creds_path):
    try:
        cred = credentials.Certificate(firebase_creds_path)
        firebase_admin.initialize_app(cred)
        print("[OK] Firebase Admin SDK inicializado exitosamente")
    except Exception as e:
        print(f"[!] Error inicializando Firebase: {e}")
else:
    # Fallback para Vercel o entornos sin archivo físico (usando variables de entorno)
    firebase_config = os.environ.get('FIREBASE_CONFIG_JSON')
    if firebase_config:
        import json
        try:
            cred_dict = json.loads(firebase_config)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("[OK] Firebase Admin SDK inicializado (vía ENV)")
        except Exception as e:
            print(f"[!] Error inicializando Firebase vía ENV: {e}")
    else:
        print("[!] Firebase no inicializado: falta el archivo de credenciales")

# Importar modelos y rutas
from models import *
# Legacy routes removed in favor of modular Blueprints
# from routes import *
# from routes_contacto import *
# from routes_clientes import *

# Blueprints
from blueprints.auth import auth_bp
from blueprints.store_public import store_public_bp
from blueprints.clients import clients_bp
from blueprints.payments import payments_bp
from blueprints.google_auth import google_auth_bp

# Blueprints de admin — módulos por dominio
from blueprints.admin import admin_blueprints

app.register_blueprint(auth_bp)
app.register_blueprint(store_public_bp)
app.register_blueprint(clients_bp)
app.register_blueprint(payments_bp, url_prefix='/api/payments')
app.register_blueprint(google_auth_bp)

for bp in admin_blueprints:
    app.register_blueprint(bp)

# ==================== DEBUG ROUTES ====================
@app.route('/api/public/debug-promotions', methods=['GET'])
def debug_promotions():
    try:
        from models import TipoPromocion
        tipos = TipoPromocion.query.all()
        return jsonify({
            'status': 'success',
            'count': len(tipos),
            'data': [t.to_dict() for t in tipos]
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== BACKGROUND SCHEDULER ====================
from apscheduler.schedulers.background import BackgroundScheduler
from cleanup_jobs import eliminar_pedidos_expirados
from newsletter_jobs import process_scheduled_newsletters
import atexit

scheduler = BackgroundScheduler()

# 1. Limpieza de pedidos cada 1 hora
scheduler.add_job(
    func=eliminar_pedidos_expirados,
    trigger="interval",
    hours=1,
    args=[app],
    id='cleanup_expired_orders',
    name='Eliminar pedidos expirados no aprobados',
    replace_existing=True
)

# 2. Procesamiento de Newsletter cada 1 minuto
scheduler.add_job(
    func=process_scheduled_newsletters,
    trigger="interval",
    minutes=1,
    args=[app],
    id='process_newsletters',
    name='Enviar newsletters programados',
    replace_existing=True
)

# Iniciar scheduler solo si no está ya corriendo y evitar duplicados en modo debug
if not scheduler.running:
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        scheduler.start()
        print("[OK] Background scheduler iniciado (Cleanup & Newsletter)")
    else:
        print("[OK] Background scheduler esperando al proceso principal...")

# Apagar scheduler al cerrar la app
atexit.register(lambda: scheduler.shutdown())

# Crear tablas
with app.app_context():
    db.create_all()



    if 'postgres' in app.config['SQLALCHEMY_DATABASE_URI']:
        # Migraciones para Admins
        try:
            db.session.execute(text("ALTER TABLE admins ADD COLUMN IF NOT EXISTS email VARCHAR(120)"))
            db.session.execute(text("UPDATE admins SET email = username || '@elvestuario.com' WHERE email IS NULL"))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Nota: Error en migración admins: {e}")

        # Migraciones para Clientes
        try:
            db.session.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)"))
            db.session.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS telefono_verificado BOOLEAN DEFAULT FALSE"))
            db.session.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS codigo_verificacion VARCHAR(6)"))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Nota: Error en migración clientes: {e}")

        # Migraciones para Pedidos
        try:
            db.session.execute(text("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS external_id VARCHAR(100)"))
            db.session.execute(text("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS comprobante_url VARCHAR(500)"))
            db.session.execute(text("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS codigo_pago_unico VARCHAR(50)"))
            db.session.execute(text("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS cliente_dni VARCHAR(20)"))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Nota: Error en migración pedidos: {e}")

        # Migraciones para Promociones
        try:
            db.session.execute(text("ALTER TABLE promociones_productos ADD COLUMN IF NOT EXISTS es_cupon BOOLEAN DEFAULT FALSE"))
            db.session.execute(text("ALTER TABLE promociones_productos ADD COLUMN IF NOT EXISTS codigo VARCHAR(50)"))
            db.session.execute(text("ALTER TABLE promociones_productos ADD COLUMN IF NOT EXISTS envio_gratis BOOLEAN DEFAULT FALSE"))
            db.session.execute(text("ALTER TABLE promociones_productos ADD COLUMN IF NOT EXISTS compra_minima FLOAT DEFAULT 0.0"))
            db.session.execute(text("ALTER TABLE promociones_productos ADD COLUMN IF NOT EXISTS max_usos INTEGER"))
            db.session.execute(text("ALTER TABLE promociones_productos ADD COLUMN IF NOT EXISTS usos_actuales INTEGER DEFAULT 0"))
            db.session.execute(text("ALTER TABLE promociones_productos ADD COLUMN IF NOT EXISTS alcance VARCHAR(20) DEFAULT 'producto'"))
            # Asegurar que fecha_fin sea nullable (para promociones indefinidas)
            db.session.execute(text("ALTER TABLE promociones_productos ALTER COLUMN fecha_fin DROP NOT NULL"))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Nota: Error en migración promociones: {e}")

        # Migraciones para Tipos de Promoción
        try:
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS tipos_promocion (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL,
                    descripcion TEXT
                )
            """))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Nota: Error en creación tipos_promocion: {e}")

        # Migraciones para Categorías
        try:
            db.session.execute(text("ALTER TABLE categorias ADD COLUMN IF NOT EXISTS slug VARCHAR(100)"))
            db.session.execute(text("ALTER TABLE categorias ADD COLUMN IF NOT EXISTS imagen VARCHAR(500)"))
            db.session.execute(text("ALTER TABLE categorias ADD COLUMN IF NOT EXISTS orden INTEGER DEFAULT 0"))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Nota: Error en migración categorías: {e}")

        # Migraciones para Productos
        try:
            db.session.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS precio_base FLOAT"))
            db.session.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS precio_descuento FLOAT"))
            db.session.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS color VARCHAR(100)"))
            db.session.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS color_hex VARCHAR(7)"))
            db.session.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS dorsal VARCHAR(100)"))
            db.session.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS numero INTEGER"))
            db.session.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS version VARCHAR(50)"))
            db.session.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS producto_relacionado_id INTEGER"))
            db.session.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS ventas_count INTEGER DEFAULT 0"))
            db.session.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Nota: Error en migración productos: {e}")

        # Migración de datos precios
        try:
            db.session.execute(text("UPDATE productos SET precio_base = precio WHERE precio_base IS NULL"))
            db.session.execute(text("UPDATE productos SET precio_descuento = precio_oferta WHERE precio_descuento IS NULL"))
            db.session.commit()
        except Exception: db.session.rollback()

        # Migraciones para StockTalles
        try:
            db.session.execute(text("ALTER TABLE stock_talles ADD COLUMN IF NOT EXISTS color_id INTEGER"))
            db.session.execute(text("ALTER TABLE stock_talles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Nota: Error en migración stock_talles: {e}")

        # Seeding de Métodos de Pago
        try:
            from models import MetodoPago
            # Verificar si existe ID 1
            id1 = db.session.execute(text("SELECT id FROM metodos_pago WHERE id = 1")).fetchone()
            if not id1:
                # Insertar transferencia como ID 1 manualmente para resolver la FK
                db.session.execute(text("""
                    INSERT INTO metodos_pago (id, nombre, descripcion, activo) 
                    VALUES (1, 'transferencia', 'Transferencia bancaria', true)
                    ON CONFLICT (id) DO NOTHING
                """))
                # Sincronizar secuencia
                db.session.execute(text("SELECT setval('metodos_pago_id_seq', (SELECT max(id) FROM metodos_pago))"))
                db.session.commit()
                print("[OK] Método de pago ID 1 restaurado.")
            
            # Asegurar existencia de otros métodos básicos
            metodos_basicos = [
                ('mercadopago', 'Mercado Pago (Tarjeta)'),
                ('efectivo_local', 'Efectivo en el Local (15% OFF)'),
                ('efectivo', 'Efectivo / Rapipago / Pago Fácil')
            ]
            for nombre, desc in metodos_basicos:
                exists = MetodoPago.query.filter_by(nombre=nombre).first()
                if not exists:
                    new_m = MetodoPago(nombre=nombre, descripcion=desc, activo=True)
                    db.session.add(new_m)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Nota: Error en seeding metodos_pago: {e}")
            print(f"Nota: Error en migración stock: {e}")

        # Constraints (en bloques separados por si ya existen)
        try:
            db.session.execute(text("ALTER TABLE productos ADD CONSTRAINT fk_producto_relacionado FOREIGN KEY (producto_relacionado_id) REFERENCES productos(id)"))
            db.session.commit()
        except Exception: db.session.rollback()

        try:
            db.session.execute(text("ALTER TABLE stock_talles ADD CONSTRAINT fk_stock_color FOREIGN KEY (color_id) REFERENCES colores(id)"))
            db.session.commit()
        except Exception: db.session.rollback()

        # Migraciones para Imagenes (Corregido nombre de tabla a plural)
        try:
            db.session.execute(text("ALTER TABLE imagenes_productos ADD COLUMN IF NOT EXISTS orden INTEGER DEFAULT 0"))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Nota: Error en migración imágenes: {e}")

        print("[OK] Verificacion de esquema PostgreSQL completada")

    # Crear admin por defecto de forma segura
    from werkzeug.security import generate_password_hash
    
    admin = Admin.query.filter_by(username='admin').first()
    # Usar variable de entorno o contraseña fija de seguridad
    initial_pass = os.environ.get('ADMIN_INITIAL_PASSWORD', 'cambiar-pass-admin')
    
    if initial_pass:
        initial_pass = initial_pass.strip() # Limpiar posibles espacios accidentales
        if not admin:
            default_admin = Admin(
                username='admin',
                password_hash=generate_password_hash(initial_pass),
                email='admin@elvestuario.com'
            )
            db.session.add(default_admin)
            db.session.commit()
            print("[OK] Admin inicial 'admin' creado exitosamente.")
        else:
            # Solo actualizamos si el password cambió o el hash es inválido para el pass actual
            from werkzeug.security import check_password_hash
            print(f"DEBUG STARTUP: Verificando admin con pass de longitud {len(initial_pass)}...")
            if not check_password_hash(admin.password_hash, initial_pass):
                admin.password_hash = generate_password_hash(initial_pass)
                db.session.commit()
                print(f"[OK] Password de admin SINCRONIZADO con ENV (Pass empieza con '{initial_pass[:2]}...').") 
            else:
                print("[OK] Password de admin ya esta sincronizado y validado.")
            
    # Limpiamos imports incorrectos previos
# Health check simple que no usa BD
# Health check simple que no usa BD
@app.route('/')
def home():
    """Ruta raíz para verificar que el servidor responde"""
    db_type = "PostgreSQL" if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres') else "SQLite"
    return jsonify({
        "status": "online",
        "database_engine": db_type,
        "message": "Backend de El Vestuario",
        "endpoints": ["/api/health", "/api/productos", "/api/auth/login"]
    }), 200

# Health check con tipo de base de datos
@app.route('/api/health')
def health_check():
    db_type = "PostgreSQL" if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres') else "SQLite"
    return jsonify({
        "status": "ok",
        "database": db_type,
        "time": time.time()
    }), 200

# ==================== LOGGING DE PETICIONES LENTAS ====================
def register_hooks(app):
    if getattr(app, '_hooks_registered', False):
        return
        
    @app.before_request
    def start_timer():
        from flask import g, request
        # No logear health check para no ensuciar
        if request.path != '/api/health':
            print(f"DEBUG IN: {request.method} {request.path}", flush=True)
        g.start_time = time.time()

    @app.after_request
    def log_request(response):
        from flask import g, request
        
        # Headers de Seguridad endurecidos
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'none'; base-uri 'self'; object-src 'none';"
        response.headers['X-XSS-Protection'] = '1; mode=block'

        if hasattr(g, 'start_time') and request.path != '/api/health':
            duration = (time.time() - g.start_time) * 1000
            print(f"DEBUG OUT: {request.method} {request.path} - {duration:.1f}ms", flush=True)
            if duration > 100: # Solo avisar si es realmente lento > 100ms
                logger.warning(f"[!] SLOW: {request.method} {request.path} {duration:.1f}ms")
        return response
    
    app._hooks_registered = True

# Registrar hooks de logging
register_hooks(app)

# Reparar Base de Datos (Agregar columna si falta)


# Para correr la aplicación, ejecutar: python run.py

