import sys
import os
sys.path.append(os.getcwd())

from app import app
from models import db
from sqlalchemy import text

with app.app_context():
    try:
        # Get constraints for promociones_productos
        query = text("""
            SELECT conname, pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            WHERE conrelid = 'promociones_productos'::regclass;
        """)
        result = db.session.execute(query).fetchall()
        print("Constraints for 'promociones_productos':")
        for row in result:
            print(f"- {row[0]}: {row[1]}")
            
    except Exception as e:
        print(f"Error inspecting constraints: {e}")
