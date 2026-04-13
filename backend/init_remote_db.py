import os
import sys
# Set the DATABASE_URL to Neon before importing app
os.environ['DATABASE_URL'] = "postgresql://neondb_owner:npg_IPHgp2Wx3iON@ep-flat-union-aml70f82-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

from app import app, db

def init_db():
    print("Initializing Neon DB schema...")
    with app.app_context():
        db.create_all()
        print("Schema created successfully on Neon!")

if __name__ == '__main__':
    init_db()
