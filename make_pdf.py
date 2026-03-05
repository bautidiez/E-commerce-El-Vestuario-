from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def create_pdf(filename):
    doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = styles['Heading1']
    title_style.alignment = 1 # Center
    
    subtitle_style = styles['Heading2']
    subtitle_style.alignment = 1
    subtitle_style.textColor = "grey"
    
    h3_style = styles['Heading3']
    h3_style.spaceAfter = 6
    h3_style.spaceBefore = 12
    
    h4_style = styles['Heading4']
    h4_style.spaceAfter = 2
    h4_style.spaceBefore = 8
    
    body_style = styles['BodyText']
    body_style.spaceAfter = 6
    
    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Code'],
        fontSize=9,
        leading=12,
        spaceAfter=4,
        backColor="#f4f4f4",
        borderPadding=4
    )

    Story = []

    # Title
    Story.append(Paragraph("Documentacion del Proyecto: El Vestuario", title_style))
    Story.append(Paragraph("E-Commerce Deportivo Full-Stack", subtitle_style))
    Story.append(Spacer(1, 0.2 * inch))

    # 1. Resumen
    Story.append(Paragraph("1. Resumen del Proyecto", h3_style))
    resumen = (
        "El Vestuario es una plataforma de comercio electronico de indumentaria deportiva de alto rendimiento "
        "desarrollada integramente desde cero. El objetivo principal del proyecto fue construir una experiencia de "
        "compra fluida para los clientes y ofrecer un panel de administracion integral y robusto que permita "
        "gestionar toda la logica del negocio (inventario, envios y analiticas) en tiempo real.<br/><br/>"
        "La arquitectura se divide en un Frontend dinamico en Angular, y un Backend RESTful en Python (Flask) "
        "conectado a PostgreSQL."
    )
    Story.append(Paragraph(resumen, body_style))

    # 2. Modulos
    Story.append(Paragraph("2. Ubicacion del Codigo por Modulo (Panel Admin)", h3_style))
    intro = "A continuacion se detalla en que archivos exactos se gestiona cada parte de la administracion:"
    Story.append(Paragraph(intro, body_style))

    modulos = [
        {
            "titulo": "A. Gestion de Productos y Categorias",
            "desc": "Permite crear y editar el catalogo jerarquico, manejar precios base y descuento, y reordenar multiples imagenes.",
            "front": "frontend/src/app/pages/admin/productos-admin/<br/>frontend/src/app/pages/admin/categorias-admin/",
            "back": "backend/blueprints/admin/productos.py<br/>backend/blueprints/admin/categorias.py",
            "models": "backend/models/catalogo.py"
        },
        {
            "titulo": "B. Gestion estricta de Stock",
            "desc": "Administra el inventario de manera granular por Producto + Talle + Color. Incluye alertas visuales para prendas agotadas.",
            "front": "frontend/src/app/pages/admin/stock-admin/",
            "back": "backend/blueprints/admin/stock.py",
            "models": "backend/models/catalogo.py (Modelo StockTalle)"
        },
        {
            "titulo": "C. Pedidos y Envíos",
            "desc": "Manejo completo de las ordenes de compra, cobros y transicion de estados de logistica. Incluye calculador de envio.",
            "front": "frontend/src/app/pages/admin/pedidos-admin/",
            "back": "backend/blueprints/admin/pedidos.py",
            "models": "backend/models/pedidos.py"
        },
        {
            "titulo": "D. Promociones Dinámicas y Cupones",
            "desc": "Modulo para habilitar cupones por tiempo limitado o asignar descuentos porcentuales a colecciones.",
            "front": "frontend/src/app/pages/admin/promociones-admin/",
            "back": "backend/blueprints/admin/promociones.py",
            "models": "backend/models/promociones.py"
        },
        {
            "titulo": "E. Integracion Newsletter",
            "desc": "Captura en landing page de correos electronicos y suscripciones de clientes (integrado con Brevo).",
            "front": "frontend/src/app/shared/footer/ (UI)",
            "back": "backend/blueprints/misc.py (Ruta /api/newsletter/subscribe)",
            "models": "backend/models/clientes.py"
        },
        {
            "titulo": "F. Core Interfaz API (Frontend <-> Backend)",
            "desc": "Toda la comunicacion ocurre via HTTP usando Observables y esta blindada por tokens JWT en este archivo central.",
            "front": "frontend/src/app/services/api.service.ts",
            "back": "backend/app.py (Middleware CORS y Config de SQLAlchemy)",
            "models": "backend/models/base.py y backend/models/__init__.py"
        }
    ]

    for mod in modulos:
        Story.append(Paragraph(mod['titulo'], h4_style))
        Story.append(Paragraph("<b>Descripcion:</b> " + mod['desc'], body_style))
        code_text = f"<b>Frontend:</b><br/>{mod['front']}<br/><br/><b>Backend:</b><br/>{mod['back']}<br/><br/><b>Modelos DB:</b><br/>{mod['models']}"
        Story.append(Paragraph(code_text, code_style))

    doc.build(Story)

if __name__ == '__main__':
    create_pdf(r"C:\Bau\PagLauri\Documentacion_ElVestuario.pdf")
