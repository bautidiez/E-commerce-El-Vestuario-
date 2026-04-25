"""
Paquete de modelos — re-exporta todo para compatibilidad con imports existentes.

Uso: from models import *  (sigue funcionando igual que antes)
"""

from .base import db

# ── Catálogo ─────────────────────────────────────────────────────────────────
from .catalogo import (
    Categoria,
    Producto,
    Talle,
    Color,
    StockTalle,
    ImagenProducto,
    productos_relacionados,
)

# ── Admin ─────────────────────────────────────────────────────────────────────
from .admin import Admin

# ── Pedidos ───────────────────────────────────────────────────────────────────
from .pedidos import MetodoPago, Pedido, ItemPedido, NotaPedido

# ── Clientes ──────────────────────────────────────────────────────────────────
from .clientes import Cliente, Favorito, Carrito, ItemCarrito

# ── Envíos ────────────────────────────────────────────────────────────────────
from .envios import Shipment, TrackingUpdate

# ── Promociones ───────────────────────────────────────────────────────────────
from .promociones import (
    TipoPromocion,
    PromocionProducto,
    promocion_productos_link,
    promocion_categorias_link,
)

# ── Ventas externas ───────────────────────────────────────────────────────────
from .ventas import VentaExterna

# ── Marketing ─────────────────────────────────────────────────────────────────
from .marketing import NewsletterHistory, ScheduledNewsletter

__all__ = [
    'db',
    # Catálogo
    'Categoria', 'Producto', 'Talle', 'Color', 'StockTalle', 'ImagenProducto',
    'productos_relacionados',
    # Admin
    'Admin',
    # Pedidos
    'MetodoPago', 'Pedido', 'ItemPedido', 'NotaPedido',
    # Clientes
    'Cliente', 'Favorito', 'Carrito', 'ItemCarrito',
    # Envíos
    'Shipment', 'TrackingUpdate',
    # Promociones
    'TipoPromocion', 'PromocionProducto',
    'promocion_productos_link', 'promocion_categorias_link',
    # Ventas
    'VentaExterna',
    # Marketing
    'NewsletterHistory', 'ScheduledNewsletter',
]
