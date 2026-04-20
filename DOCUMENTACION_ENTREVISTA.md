# 🚀 Guía de Preparación Técnica: Proyecto PagLauri (El Vestuario)

Esta guía ha sido diseñada para que defiendas el proyecto **PagLauri** en una entrevista técnica real para un puesto de **Desarrollador Next.js Jr / Full Stack**. Aunque el proyecto usa Angular y Flask, los conceptos de arquitectura, manejo de estado y flujo de negocio son 100% transferibles.

---

## 1. Stack Tecnológico

| Capa | Tecnología | Propósito |
| :--- | :--- | :--- |
| **Frontend** | Angular 21 | Framework robusto basado en componentes para una SPA (Single Page Application) reactiva. |
| **Backend** | Python + Flask | Micro-framework ligero y escalable para la API REST. |
| **Base de Datos** | PostgreSQL (Prod) / SQLite (Dev) | Base de datos relacional para integridad de pedidos y catálogo. |
| **Autenticación** | JWT (JSON Web Tokens) | Manejo de sesiones sin estado (stateless) seguro entre front y back. |
| **Seguridad** | Google reCAPTCHA v3 | Protección contra bots en login y contacto. |
| **Email** | Brevo API (SMTP) | Envío asíncrono de confirmaciones y contacto. |
| **UI/UX** | SweetAlert2 / ngx-quill | Notificaciones modernas y editor de texto enriquecido para admin. |

---

## 2. Arquitectura del Sistema

El proyecto sigue una arquitectura **Client-Server** desacoplada mediante una **API RESTful**.

*   **Organización del Backend (Flask):**
    *   **Modular:** Uso de `Blueprints` para separar dominios (admin, público, clientes, pagos).
    *   **Capa de Servicios:** La lógica de negocio pesada reside en `services/` (ej: `OrderService`, `ProductService`), manteniendo los controladores de las rutas limpios.
    *   **Modelos:** SQLAlchemy con relaciones complejas (Many-to-Many para productos relacionados y promociones).
*   **Organización del Frontend (Angular):**
    *   **Arquitectura de Servicios:** Servicios centralizados (`ApiService`, `CartService`) inyectados mediante DI (Dependency Injection).
    *   **Manejo de Estado:** Uso de `RxJS` (BehaviorSubjects) para reactividad en tiempo real (ej: el contador del carrito).
*   **Flujo de Información:**
    1.  Usuario interactúa con un componente.
    2.  Componente llama a un método del Servicio.
    3.  Servicio realiza petición HTTP al Backend.
    4.  Flask recibe la petición, valida JWT si es necesario, y delega al Service de SQLAlchemy.
    5.  La DB responde, se transforma a JSON y viaja de vuelta al suscriptor en el componente.

---

## 3. Funcionalidades Clave del E-commerce

*   **Catálogo:** Implementado con filtros dinámicos en el servidor (búsqueda, categorías, talles, colores, precios). Implementa **paginación** para performance.
*   **Carrito de Compras:** Doble persistencia. Local (para usuarios anónimos) y Sincronizada en DB (mediante el endpoint `/api/cart`) cuando el cliente inicia sesión.
*   **Checkout:** Flujo de 4 pasos con **Reactiva Forms**. Incluye cálculo de envío dinámico mediante integración con servicios de logística (Andreani/Correo Argentino).
*   **Autenticación:** Sistema híbrido. Admin (gestión total) y Cliente (historial y carrito persistente).

---

## 4. Backend: La API

*   **Tecnología:** Flask. Elegido por su simplicidad y rapidez para prototipar.
*   **Endpoints Principales:**
    *   `GET /api/productos`: Catálogo con filtros complejos.
    *   `POST /api/orders`: Creación atómica de pedidos (valida stock y calcula total final).
    *   `POST /api/cart`: Sincronización de estado del carrito.
*   **Seguridad:** Middleware global de CORS, limitador de peticiones (`Flask-Limiter`) para prevenir ataques de fuerza bruta y validación de tokens JWT en rutas protegidas.

---

## 5. Frontend: La UI Reaccionaria

*   **Angular 21:** Aprovecha las últimas mejoras del framework (Standalone Components, Signals si aplica).
*   **Componentes:** Organización por páginas (`pages/`) y compartidos (`components/`).
*   **Manejo de Estado:** El `CartService` expone un `cart$` observable. Cualquier componente (Nav, ProductDetail, CartPage) se suscribe y reacciona a cambios automáticamente sin recargar la página.

---

## 6. Decisiones Técnicas (Justificación)

*   **¿Por qué Flask?** Porque permite un control granular sobre las rutas y es extremadamente ligero para servicios e-commerce que requieren baja latencia.
*   **¿Por qué Angular?** Por su estructura fuertemente tipada (TypeScript) y su capacidad para manejar formularios complejos (Checkout) de forma robusta con `ReactiveFormsModule`.
*   **Limitaciones:** Al ser una SPA pura, el SEO inicial es un reto comparado con Next.js (SSR). **Mejoraría esto implementando Angular Universal o migrando a Next.js para renderizado en el servidor.**

---

## 7. Preguntas de Entrevista (Simulacro)

### Nivel Básico (10)
1.  **¿Cómo manejas el paso de datos entre componentes?** -> Input/Output para padres/hijos y Servicios para componentes distantes.
2.  **¿Para qué usas JWT?** -> Para autenticar al usuario sin guardar sesiones en el servidor.
3.  **¿Qué es un Observable en tu proyecto?** -> Como el flujo del carrito que avisa cambios a toda la app.
4.  **¿Cómo proteges una ruta en Angular?** -> Usando `AuthGuard` implementando la interfaz `CanActivate`.
5.  **¿Qué base de datos usas y por qué relacional?** -> PostgreSQL, por la necesidad de transacciones seguras (Pedidos no pueden quedar a medias).
6.  **¿Cómo manejas errores HTTP?** -> Mediante Interceptores o bloques `error` en los `subscribe`.
7.  **¿Diferencia entre `precio_base` y `precio_descuento` en tu DB?** -> Permite mostrar el "tachado" y manejar liquidaciones sin perder el valor original.
8.  **¿Cómo evitas que un bot envíe formularios?** -> reCAPTCHA v3 integrado en el backend.
9.  **¿Qué hace el archivo `requirements.txt`?** -> Lista las dependencias de Python necesarias para correr el backend.
10. **¿Cómo estilizas los componentes?** -> CSS modular por componente para evitar fugas de estilos.

### Nivel Intermedio (10)
1.  **¿Cómo implementaste la lógica de stock bajo?** -> Método `tiene_stock_bajo()` en el modelo `Producto` (umbral entre 1 y 3).
2.  **¿Qué es el patrón Service en Flask?** -> Separar la lógica que toca la DB fuera de la ruta para que sea testeable y reutilizable.
3.  **¿Cómo manejas el carrito si el usuario no está logueado?** -> Persiste en el `localStorage` del navegador.
4.  **¿Cómo calculas el envío en el Checkout?** -> Envío el código postal y los items al backend, que consulta las reglas de negocio de logística.
5.  **¿Por qué usas Blueprints en Flask?** -> Para que `app.py` no sea un archivo de 2000 líneas; organiza por dominios (Auth, Admin, Store).
6.  **¿Cómo previenes el N+1 en las consultas de productos?** -> Usando `joinedload` o `selectinload` en SQLAlchemy para traer imágenes y stock en una sola query.
7.  **¿Cómo manejas la carga de imágenes?** -> Guardo la ruta en la DB y el archivo físico en `static/uploads/`.
8.  **¿Qué es la sincronización del carrito?** -> Al loguearse, el front envía el carrito local al back y este mezcla o sobreescribe el carrito en la DB.
9.  **¿Cómo manejas promociones tipo 2x1 en el código?** -> Una clase `PromocionProducto` con un método `calcular_descuento(cantidad, precio)`.
10. **¿Cómo garantizas que el frontend es responsive?** -> Media queries de CSS nativo y Flexbox/Grid.

### Nivel Difícil (10)
1.  **¿Cómo resolverías un problema de "Race Condition" en el stock?** -> Usar bloqueos en la transacción de la DB (`select for update`) al momento de pagar.
2.  **¿Cómo harías este proyecto escalable para 1 millón de productos?** -> Indexación en PostgreSQL, usar Redis para caché de catálogo y migrar imágenes a un S3.
3.  **¿Cómo migrarías este proyecto a Next.js?** -> Pasaría los Servicios de Angular a Hooks de React y las rutas de Flask a API Routes o Server Actions.
4.  **¿Cómo manejas las transacciones atómicas en pedidos?** -> Usando el context manager de SQLAlchemy; si falla el descuento de stock, se revierte la creación del pedido.
5.  **¿Qué patrón de diseño usas en Angular?** -> Singleton para servicios y Observer para reactividad.
6.  **¿Cómo optimizas el bundle size del frontend?** -> Lazy loading de módulos y Tree-shaking.
7.  **¿Cómo manejas el despliegue (Deploy)?** -> Usando `Procfile` para Gunicorn en plataformas como Render o Heroku.
8.  **¿Cómo implementaste la búsqueda de productos?** -> Operadores `or_` e `ilike` en SQLAlchemy para buscar en nombre y descripción simultáneamente.
9.  **¿Cómo manejas el estado global sin NgRx?** -> Con Servicios Singleton y `BehaviorSubjects` de RxJS; es suficiente para un e-commerce de este tamaño.
10. **¿Cómo proteges secretos (API Keys)?** -> Usando variables de entorno (`.env`) cargadas con `python-dotenv`.

---

## 8. "Muéstrame el Código" (Puntos Clave)

Cuando te pidan mostrar código, abre estos archivos y di esto:

*   **El Carrito:**
    *   **Archivo:** `frontend/src/app/services/cart.service.ts`
    *   **Qué decir:** "Aquí manejo el estado reactivo del carrito usando un `BehaviorSubject`. Esto permite que cualquier componente se entere de cambios en tiempo real sin recargar."
*   **Consumo de API:**
    *   **Archivo:** `frontend/src/app/services/api.service.ts`
    *   **Qué decir:** "Centralizo todas las llamadas HTTP aquí para manejar cabeceras de autenticación JWT de forma consistente en un solo lugar."
*   **Lógica de Negocio (Pedido):**
    *   **Archivo:** `backend/blueprints/store_public.py` (ruta `create_pedido`)
    *   **Qué decir:** "Aquí recibo la orden y delego al `OrderService`. Es un proceso atómico: validamos stock, calculamos el total final en el servidor (nunca confío en el precio del front) y disparamos el email."
*   **Modelo de Datos:**
    *   **Archivo:** `backend/models.py`
    *   **Qué decir:** "Diseñé un esquema relacional que soporta variantes (talles/colores) y promociones flexibles. Uso índices en columnas de búsqueda para optimizar el rendimiento."

---

## 9. Debilidades y Mejoras

| Debilidad | Justificación en Entrevista | Mejora Propuesta (Jr) | Mejora Propuesta (Mid) |
| :--- | :--- | :--- | :--- |
| SEO en SPA | "Prioricé la experiencia de usuario fluida y el panel de administración complejo." | Implementar Meta Tags dinámicos. | Migrar a Next.js para SSR (Server Side Rendering). |
| Gestión de Estado | "Servicios con RxJS son eficaces para este volumen de datos." | Usar Signals (Angular 17+). | Implementar Redux/NgRx para trazabilidad total. |
| Imágenes locales | "Es un MVP funcional para hosting compartido/vps." | Compresión de imágenes antes de subir. | Implementar Cloudinary o AWS S3 para assets. |

---

## 10. Flujo Completo del Usuario

1.  **Entrada:** El usuario accede a la Home (SSR parcial o carga de catálogo total).
2.  **Selección:** Filtra por categoría -> El front pide a `/api/productos?categoria_id=X`.
3.  **Carrito:** Agrega un talle M -> El `CartService` actualiza el `localStorage` y dispara un evento al Nav.
4.  **Checkout:** Completa 4 pasos (Datos -> Envío -> Pago -> Confirmación).
    *   *Backend:* Valida stock real -> Crea `Pedido` -> Resta `StockTalle`.
5.  **Cierre:** Se genera el número de pedido y se envía el comprobante por email vía Brevo.

---

## 11. Elevator Pitch (1 Minuto)

> "Desarrollé **El Vestuario**, un e-commerce Full Stack robusto diseñado para la venta de ropa deportiva. Utilicé **Angular 21** para una experiencia de usuario fluida y reactiva, y un backend en **Python/Flask** con una arquitectura de servicios desacoplada. Implementé un sistema de checkout complejo de 4 pasos con integración de logística real, gestión de stock por variantes (talle/color) y un panel de administración completo con estadísticas de ventas. Mi enfoque estuvo en la integridad de los datos, usando **PostgreSQL/SQLAlchemy** para asegurar que cada pedido y movimiento de stock sea atómico, y en la seguridad, integrando **JWT** y **reCAPTCHA**. Es un proyecto que demuestra mi capacidad para manejar flujos de negocio reales y arquitecturas modernas de componentes."

---

## 12. Puente Angular -> Next.js (Para tu entrevista)

Si te preguntan por qué sabes Next.js si hiciste esto en Angular:

*   *"Angular me enseñó la importancia del tipado con **TypeScript** y la modularidad de los componentes. En Next.js, aplico estos conceptos usando **Hooks** en lugar de Servicios y sustituyo la inyección de dependencias por **Context API**. Además, entiendo perfectamente el ciclo de vida de los componentes, lo que me facilita manejar **Server y Client Components** en Next.js."*

---

## 🛠️ Desarrollo de Experiencia (Para CV / LinkedIn / Entrevista)

Usa estos puntos para describir tu rol en este proyecto:

### **Rol: Desarrollador Full Stack (Proyecto El Vestuario)**

**Responsabilidades y Logros:**
*   **Diseño de Aplicación de Gran Escala:** Lideré el desarrollo de una SPA con **Angular 21** conectada a una API REST en **Flask**, gestionando más de 15 esquemas de datos relacionales en **PostgreSQL**.
*   **Optimización de Performance:** Reduje el tiempo de respuesta del catálogo implementando navegación paginada en el servidor y previniendo el problema de consultas N+1 mediante el uso estratégico de `selectinload` en SQLAlchemy.
*   **Implementación de Lógica de Negocio Compleja:** Desarrollé un sistema de promociones flexible (2x1, 3x2, descuentos porcentuales y cupones) que se autogestiona desde el panel administrativo, asegurando que los cálculos finales se realicen siempre en el servidor para evitar fraudes.
*   **Integración de Logística y Pagos:** Programé la integración con servicios de correo (Andreani/Correo Argentino) para el cálculo dinámico de costos de envío basado en el código postal y el volumen total del carrito.
*   **Foco en Seguridad:** Implementé autenticación robusta mediante **JWT**, protección de formularios con **Google reCAPTCHA v3** y sanitización de entradas de datos para prevenir inyecciones SQL.
*   **Migración e Infraestructura:** Gestioné la migración de base de datos de SQLite a PostgreSQL para entornos de producción y configuré el entorno de ejecución mediante variables de entorno y Gunicorn para asegurar un despliegue estable.

**Tecnologías Clave Utilizadas:**
*   **Frontend:** Angular, TypeScript, RxJS, Reactive Forms, CSS Grid/Flexbox.
*   **Backend:** Python, Flask, SQLAlchemy, JWT, Flask-Mail (Brevo API).
*   **DevOps/Herramientas:** PostgreSQL, Git, POSTMAN para pruebas de API, Vercel/Render.

