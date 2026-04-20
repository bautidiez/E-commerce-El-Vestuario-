import os
import psycopg2

def check_db():
    conn = psycopg2.connect("postgresql://postgres:bauti123@127.0.0.1:5432/elvestuario")
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM admins")
    admins = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM productos")
    productos = cur.fetchone()[0]
    print(f"Admins: {admins}")
    print(f"Productos: {productos}")

if __name__ == '__main__':
    check_db()
