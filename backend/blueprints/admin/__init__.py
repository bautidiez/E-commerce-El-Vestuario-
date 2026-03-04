"""
Sub-paquete de blueprints del panel admin.
Registra todos los blueprints de administración.
"""
from .estadisticas import estadisticas_bp
from .productos import productos_bp
from .categorias import categorias_bp
from .stock import stock_bp
from .pedidos import pedidos_bp
from .ventas_externas import ventas_externas_bp
from .promociones import promociones_bp
from .misc import misc_bp

# Lista de todos los blueprints admin para registro en app.py
admin_blueprints = [
    estadisticas_bp,
    productos_bp,
    categorias_bp,
    stock_bp,
    pedidos_bp,
    ventas_externas_bp,
    promociones_bp,
    misc_bp,
]

__all__ = ['admin_blueprints']
