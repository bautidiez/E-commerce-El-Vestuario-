@echo off
echo ========================================
echo   INICIANDO FRONTEND - EL VESTUARIO
echo ========================================
echo.

cd frontend

echo [1/2] Verificando dependencias...
if not exist "node_modules" (
    echo Instalando dependencias por primera vez...
    call npm install
)

echo [2/2] Iniciando servidor Angular...
echo.
echo ========================================
echo   Frontend corriendo en: http://localhost:4200
echo   Presiona Ctrl+C para detener
echo ========================================
echo.

call npm start

pause
