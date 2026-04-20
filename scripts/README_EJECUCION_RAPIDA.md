# ⚡ INICIO RÁPIDO - El Vestuario

## 🚀 Método 1: Scripts Automáticos (MÁS FÁCIL)

### Windows:

1. **Iniciar Backend:**
   - Doble clic en `INICIAR_BACKEND.bat`
   - Espera a que aparezca: "Servidor corriendo en: http://localhost:5000"

2. **Iniciar Frontend:**
   - Abre una **nueva ventana** y doble clic en `INICIAR_FRONTEND.bat`
   - Espera a que aparezca: "Frontend corriendo en: http://localhost:4200"

3. **Abrir en el navegador:**
   - Ve a: **http://localhost:4200**

---

## 🖥️ Método 2: Manual (Paso a Paso)

### TERMINAL 1 - Backend:

```powershell
# 1. Ir a la carpeta backend
cd C:\Bau\PagLauri\backend

# 2. Activar entorno virtual
.\venv\Scripts\Activate.ps1

# 3. Instalar dependencias (solo primera vez)
pip install -r requirements.txt

# 4. Ejecutar migraciones (solo primera vez)
python migrar_columnas.py
python agregar_categorias.py

# 5. Iniciar servidor
python app.py
```

**✅ Listo cuando veas:**
```
 * Running on http://0.0.0.0:5000
```

### TERMINAL 2 - Frontend:

```powershell
# 1. Ir a la carpeta frontend
cd C:\Bau\PagLauri\frontend

# 2. Instalar dependencias (solo primera vez)
npm install

# 3. Iniciar servidor
ng serve
```

**✅ Listo cuando veas:**
```
✔ Compiled successfully.
** Angular Live Development Server is listening on localhost:4200 **
```

---

## 🌐 Acceder a la Aplicación

- **Tienda (Frontend)**: http://localhost:4200
- **API (Backend)**: http://localhost:5000/api
- **Panel Admin**: http://localhost:4200/admin/login

### Credenciales Admin:
- **Usuario**: `admin`
- **Contraseña**: `admin123`

---

## ✅ Verificación Rápida

1. ✅ Backend corriendo en puerto 5000
2. ✅ Frontend corriendo en puerto 4200
3. ✅ Puedes acceder a http://localhost:4200
4. ✅ El buscador funciona en el header
5. ✅ Los filtros funcionan en la página de productos

---

## 🔧 Solución de Problemas

### Error: "ModuleNotFoundError"
```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Error: "Cannot find module"
```powershell
cd frontend
npm install
```

### Error: "Port already in use"
- Cierra otros programas que usen los puertos 5000 o 4200
- O cambia los puertos en los archivos de configuración

---

## 📚 Documentación Completa

Para más detalles, consulta: **GUIA_EJECUCION.md**

---

## 🎉 ¡Listo!

Una vez que ambos servidores estén corriendo, puedes usar todas las funcionalidades:
- ✅ Buscador de productos
- ✅ Filtros avanzados
- ✅ Ordenamiento
- ✅ Panel de administración
- ✅ Gestión completa de productos
