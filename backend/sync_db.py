import sqlite3
import os
import sys

# La URL de PostgreSQL a donde vamos a insertar
POSTGRES_URL = "postgresql://elvestuario_user:IbkOl9uuqKVHSae7WWJ9nPox6mXl9YSC@dpg-d5nqgrngi27c73ea03hg-a/elvestuario"

# OJO: dpg-d5nqgrngi27c73ea03hg-a es un hostname interno de Render que NO funciona desde mi PC local.
# Necesitamos la EXTERNAL URL de Supabase / Neon o de este mismo si es Render expuesto.
# Como el usuario me pegó la URL de su conexión, la voy a revisar.

print("Para transferir los productos a esta nueva base, necesito usar la EXTERNAL URL que te provee Render en la sección de 'Connections'.")
