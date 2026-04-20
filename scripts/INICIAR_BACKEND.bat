@echo off
echo ========================================
echo   INICIANDO BACKEND - EL VESTUARIO
echo ========================================
echo.

cd backend

echo [1/4] Activando entorno virtual...
call venv\Scripts\activate.bat

echo [2/4] Verificando dependencias...
pip install -r requirements.txt --quiet

echo [3/4] Ejecutando migraciones...
python migrar_columnas.py
python agregar_categorias.py
python migrar_colores_stock.py
python migrar_categoria_padre.py
python reorganizar_categorias_sqlite.py

echo [4/4] Iniciando servidor Flask...
echo.
echo ========================================
echo   Servidor corriendo en: http://localhost:5000
echo   Presiona Ctrl+C para detener
echo ========================================
echo.

python app.py

pause
