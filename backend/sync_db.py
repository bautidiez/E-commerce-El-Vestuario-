import sqlite3
import os
import sys

# La URL de PostgreSQL a donde vamos a insertar
POSTGRES_URL = os.environ.get("POSTGRES_URL")
if not POSTGRES_URL:
    print("ERROR: POSTGRES_URL environment variable is required.")
    sys.exit(1)

# OJO: dpg-d5nqgrngi27c73ea03hg-a es un hostname interno de Render que NO funciona desde mi PC local.
# Necesitamos la EXTERNAL URL de Supabase / Neon o de este mismo si es Render expuesto.
# Como el usuario me pegó la URL de su conexión, la voy a revisar.

print("Para transferir los productos a esta nueva base, necesito usar la EXTERNAL URL que te provee Render en la sección de 'Connections'.")
