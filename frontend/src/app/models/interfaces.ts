export interface Categoria {
    id: number;
    nombre: string;
    slug?: string;
    descripcion?: string;
    imagen?: string;
    orden?: number;
    categoria_padre_id?: number;
    subcategorias?: Categoria[];
    nivel?: number;
}

export interface Talle {
    id: number;
    nombre: string;
    orden?: number;
}

export interface Color {
    id: number;
    nombre: string;
    codigo_hex?: string;
}

export interface StockTalle {
    id: number;
    producto_id: number;
    talle_id: number;
    color_id?: number;
    cantidad: number;
    talle?: Talle;
    color?: Color;
}

export interface ImagenProducto {
    id: number;
    producto_id: number;
    url: string;
    es_principal: boolean;
    orden: number;
}

export interface Promocion {
    id: number;
    tipo_promocion_nombre: string;
    valor: number;
    activa: boolean;
    fecha_inicio: string;
    fecha_fin: string;
    envio_gratis?: boolean;
    compra_minima?: number;
    es_cupon?: boolean;
    codigo?: string;
}

export interface Producto {
    id: number;
    nombre: string;
    descripcion?: string;
    precio_base: number;
    precio_descuento?: number;
    categoria_id: number;
    categoria?: Categoria;

    activo: boolean;
    destacado: boolean;

    // Variantes opcionales
    color?: string;
    color_hex?: string;
    dorsal?: string;
    numero?: number;
    version?: string;

    // Relaciones
    stock_talles?: StockTalle[];
    imagenes?: ImagenProducto[];
    promociones?: Promocion[];

    // Helpers frontend
    precio_actual?: number;
}

export interface CartItem {
    producto: Producto;
    talle: Talle;
    cantidad: number;
    precio_unitario: number;
    descuento?: number;
}

export interface EnvioOption {
    id: string;
    nombre: string;
    costo: number;
    descuento?: boolean; // True si es envío gratis
    tiempo_estimado?: string;
    modalidad?: string; // 'domicilio' | 'sucursal'
    img?: string;
}

// Constantes de Configuración
export const CONFIG = {
    CATEGORIAS: {
        IDS_SHORTS: [2, 8] // IDs históricos de shorts
    }
};
