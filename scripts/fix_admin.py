import sys
import os
sys.path.append('backend')
from backend.app import db, app
from backend.models import Admin
from werkzeug.security import generate_password_hash

os.environ['DATABASE_URL']="postgresql://neondb_owner:npg_IPHgp2Wx3iON@ep-flat-union-aml70f82-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

with app.app_context():
    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(username='admin', email='admin@elvestuario.com', password_hash=generate_password_hash('admin'))
        db.session.add(admin)
        db.session.commit()
        print("Admin user created with password 'admin'")
    else:
        print("Admin user already exists")
