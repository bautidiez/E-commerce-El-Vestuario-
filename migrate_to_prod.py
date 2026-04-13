"""
Script de migración: SQLite local → PostgreSQL de producción (Render)
Uso: python migrate_to_prod.py <EXTERNAL_POSTGRES_URL>
Ejemplo: python migrate_to_prod.py postgresql://user:pass@host:5432/db
"""
import sqlite3
import sys
import os

SQLITE_PATH = r'c:\Bau\PagLauri\backend\instance\elvestuario.db'

def get_sqlite_data():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    tables_order = [
        'admins', 'tipos_promocion', 'metodos_pago',
        'categorias', 'talles', 'colores',
        'productos', 'stock_talles', 'imagenes_productos',
        'promociones_productos', 'ventas_externas',
    ]

    data = {}
    for table in tables_order:
        try:
            c.execute(f"SELECT * FROM [{table}]")
            rows = c.fetchall()
            if rows:
                cols = [d[0] for d in c.description]
                data[table] = (cols, [list(r) for r in rows])
                print(f"  {table}: {len(rows)} filas")
            else:
                data[table] = None
                print(f"  {table}: vacia")
        except Exception as e:
            print(f"  {table}: ERROR - {e}")
            data[table] = None
    conn.close()
    return data

def migrate(pg_url, data):
    try:
        import psycopg2
    except ImportError:
        print("Instalando psycopg2...")
        os.system("pip install psycopg2-binary -q")
        import psycopg2

    if '?' not in pg_url:
        pg_url += '?sslmode=require'
    elif 'sslmode=' not in pg_url:
        pg_url += '&sslmode=require'
        
    conn = psycopg2.connect(pg_url)
    conn.autocommit = True
    cur = conn.cursor()

    # Desactivar FK checks temporalmente
    # Desactivar FK checks temporalmente (skip for Neon)

    COLUMN_MAP = {
        # Columnas que existen en SQLite pero pueden no estar en Postgres tal cual
        # Se excluyen las que no existen
    }

    # Columnas esperadas en PostgreSQL por tabla (las que definimos en models)
    PG_COLUMNS = {
        'admins': ['id', 'username', 'email', 'password_hash', 'created_at'],
        'tipos_promocion': ['id', 'nombre', 'descripcion'],
        'metodos_pago': ['id', 'nombre', 'descripcion', 'activo'],
        'categorias': ['id', 'nombre', 'descripcion', 'categoria_padre_id', 'activa', 'created_at', 'imagen', 'orden'],
        'talles': ['id', 'nombre', 'orden'],
        'colores': ['id', 'nombre', 'codigo_hex', 'created_at'],
        'productos': ['id', 'nombre', 'descripcion', 'precio_base', 'precio_descuento',
                      'categoria_id', 'activo', 'destacado', 'color', 'color_hex',
                      'dorsal', 'numero', 'version', 'producto_relacionado_id',
                      'ventas_count', 'created_at', 'updated_at'],
        'stock_talles': ['id', 'producto_id', 'color_id', 'talle_id', 'cantidad', 'created_at', 'updated_at'],
        'imagenes_productos': ['id', 'producto_id', 'url', 'es_principal', 'orden', 'created_at'],
        'promociones_productos': ['id', 'alcance', 'tipo_promocion_id', 'valor', 'es_cupon',
                                   'codigo', 'envio_gratis', 'activa', 'fecha_inicio', 'fecha_fin',
                                   'compra_minima', 'max_usos', 'usos_actuales', 'created_at'],
        'ventas_externas': ['id', 'producto_id', 'talle_id', 'cantidad', 'precio_unitario',
                            'ganancia_total', 'fecha', 'admin_id', 'notas', 'created_at'],
    }

    for table, pg_cols in PG_COLUMNS.items():
        if not data.get(table):
            print(f"  SKIP {table} (sin datos)")
            continue

        sqlite_cols, rows = data[table]

        # Mapear columnas disponibles de SQLite a las esperadas en PG
        col_indices = {}
        for pg_col in pg_cols:
            if pg_col in sqlite_cols:
                col_indices[pg_col] = sqlite_cols.index(pg_col)

        if not col_indices:
            print(f"  SKIP {table} (sin columnas compatibles)")
            continue

        # Borrar datos existentes en PG
        cur.execute(f"DELETE FROM {table}")

        inserted = 0
        errors = 0
        for row in rows:
            values = []
            for pg_col in pg_cols:
                if pg_col in col_indices:
                    val = row[col_indices[pg_col]]
                    # Convert SQLite integers (1/0) to Python bools for PostgreSQL BOOLEAN columns
                    bool_columns = ['activa', 'activo', 'destacado', 'es_cupon', 'envio_gratis', 'es_principal']
                    if pg_col in bool_columns and val is not None:
                        val = bool(val)
                    values.append(val)
                else:
                    values.append(None)

            placeholders = ', '.join(['%s'] * len(pg_cols))
            col_names = ', '.join(pg_cols)
            sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            try:
                cur.execute(sql, values)
                inserted += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    import traceback
                    traceback.print_exc()
                    print(f"    ERROR en fila de {table}: {repr(e)}")

        print(f"  {table}: {inserted} insertadas, {errors} errores")

        # Resetear secuencias para que los IDs siguientes no choquen
        try:
            cur.execute(f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 1))")
        except:
            pass  # Tabla sin secuencia o sin columna id

    # Reactivar FK checks (skip for Neon)
    conn.commit()
    cur.close()
    conn.close()
    print("\nMigracion completada!")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python migrate_to_prod.py <EXTERNAL_POSTGRES_URL>")
        print("")
        print("La External URL la encontras en Render > tu database > External Database URL")
        print("Formato: postgresql://user:pass@host:5432/dbname")
        sys.exit(1)

    pg_url = sys.argv[1]
    print(f"Leyendo datos de SQLite: {SQLITE_PATH}")
    data = get_sqlite_data()
    print(f"\nMigrando a PostgreSQL: {pg_url[:40]}...")
    migrate(pg_url, data)
