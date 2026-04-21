import sys
import os
sys.path.append(os.getcwd())

from app import app
from models import db
from sqlalchemy import text

with app.app_context():
    print(f"Inspecting DB: {app.config['SQLALCHEMY_DATABASE_URI']}")
    try:
        # Get column info for promociones_productos
        query = text("""
            SELECT column_name, is_nullable, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'promociones_productos';
        """)
        result = db.session.execute(query).fetchall()
        print("Column details for 'promociones_productos':")
        for row in result:
            print(f"- {row[0]}: Nullable={row[1]}, Type={row[2]}")
            
    except Exception as e:
        print(f"Error inspecting table: {e}")
