import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) { }

  getApiUrl(): string {
    return this.apiUrl;
  }

  getFormattedImageUrl(url: string | null | undefined): string {
    if (!url) return 'assets/no-img.png';
    
    // Si es una URL externa (ej: Firebase, Cloudinary directo)
    if (url.startsWith('http')) {
      return this.optimizeWithCloudinary(url);
    }

    const apiBase = this.apiUrl.replace('/api', '');
    const fullUrl = `${apiBase}${url}`;
    return this.optimizeWithCloudinary(fullUrl);
  }

  private optimizeWithCloudinary(url: string): string {
    const cloudName = (environment as any).cloudinaryCloudName;
    if (!cloudName) return url;

    // Solo optimizar si no es ya una URL de Cloudinary
    if (url.includes('cloudinary.com')) return url;

    // Wrap con Cloudinary Fetch API
    // Parámetros: w_600 (ancho), q_auto (calidad auto), f_auto (formato auto - WebP/AVIF)
    return `https://res.cloudinary.com/${cloudName}/image/fetch/w_600,c_limit,q_auto,f_auto/${url}`;
  }

  private getHeaders(url: string = ''): HttpHeaders {
    let token = localStorage.getItem('token'); // default fallback
    
    // Si la URL apunta al panel de administración, priorizar token de admin
    if (url.includes('/admin/') || url.includes('/auth/verify')) {
      token = localStorage.getItem('auth_token_admin') || token;
    } else if (url.includes('/clientes/') || url.includes('/cart')) {
      token = localStorage.getItem('auth_token_cliente') || token;
    }

    let headers = new HttpHeaders({
      'Content-Type': 'application/json'
    });
    if (token) {
      headers = headers.set('Authorization', `Bearer ${token}`);
    }
    return headers;
  }

  // Autenticación
  login(username: string, password: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/auth/login`, { username, password });
  }

  loginUnified(credenciales: { identifier: string, password: string, recaptcha_token?: string }): Observable<any> {
    return this.http.post(`${this.apiUrl}/auth/login-unified`, {
      identifier: credenciales.identifier,
      password: credenciales.password,
      recaptcha_token: credenciales.recaptcha_token
    });
  }

  verifyToken(): Observable<any> {
    const url = `${this.apiUrl}/auth/verify`;
    return this.http.get(url, { headers: this.getHeaders(url) });
  }

  verifyTokenCliente(): Observable<any> {
    const url = `${this.apiUrl}/clientes/verify`;
    return this.http.get(url, { headers: this.getHeaders(url) });
  }

  // Productos
  getProductos(filtros?: any): Observable<any> {
    let url = `${this.apiUrl}/productos`;
    const params: any = {};

    if (filtros) {
      if (filtros.busqueda) params.busqueda = filtros.busqueda;
      if (filtros.categoria_id) params.categoria_id = filtros.categoria_id;
      if (filtros.destacados !== undefined) params.destacados = filtros.destacados;
      if (filtros.color) params.color = filtros.color;
      if (filtros.talle_id) params.talle_id = filtros.talle_id;
      if (filtros.dorsal) params.dorsal = filtros.dorsal;
      if (filtros.numero !== undefined) params.numero = filtros.numero;
      if (filtros.version) params.version = filtros.version;
      if (filtros.precio_min !== undefined) params.precio_min = filtros.precio_min;
      if (filtros.precio_max !== undefined) params.precio_max = filtros.precio_max;
      if (filtros.ordenar_por) params.ordenar_por = filtros.ordenar_por;
      if (filtros.ofertas !== undefined) params.ofertas = filtros.ofertas;
      if (filtros.page !== undefined) params.page = filtros.page;
      if (filtros.page_size !== undefined) params.page_size = filtros.page_size;
      if (filtros.estado_stock) params.estado_stock = filtros.estado_stock;
      if (filtros.activos !== undefined) params.activos = filtros.activos;
    }

    const queryString = Object.keys(params).map(key => `${key}=${encodeURIComponent(params[key])}`).join('&');
    if (queryString) url += `?${queryString}`;

    return this.http.get(url);
  }

  getProducto(id: number): Observable<any> {
    return this.http.get(`${this.apiUrl}/productos/${id}`);
  }

  createProducto(producto: any): Observable<any> {
    // Limpiar y preparar datos para enviar
    const productoLimpio: any = {
      nombre: producto.nombre,
      descripcion: producto.descripcion || '',
      precio_base: parseFloat(producto.precio_base),
      categoria_id: parseInt(producto.categoria_id),
      activo: producto.activo !== undefined ? producto.activo : true,
      destacado: producto.destacado || false
    };

    if (producto.precio_descuento) {
      productoLimpio.precio_descuento = parseFloat(producto.precio_descuento);
    }

    if (producto.color) {
      productoLimpio.color = producto.color;
    }

    if (producto.color_hex) {
      productoLimpio.color_hex = producto.color_hex;
    }

    if (producto.producto_relacionado_id) {
      productoLimpio.producto_relacionado_id = parseInt(producto.producto_relacionado_id);
    }

    if (producto.dorsal) {
      productoLimpio.dorsal = producto.dorsal;
    }

    const url = `${this.apiUrl}/admin/productos`;
    return this.http.post(url, productoLimpio, { headers: this.getHeaders(url) });
  }

  updateProducto(id: number, producto: any): Observable<any> {
    const url = `${this.apiUrl}/admin/productos/${id}`;
    return this.http.put(url, producto, { headers: this.getHeaders(url) });
  }

  deleteProducto(id: number): Observable<any> {
    const url = `${this.apiUrl}/admin/productos/${id}`;
    return this.http.delete(url, { headers: this.getHeaders(url) });
  }

  deleteProductosBulk(ids: number[]): Observable<any> {
    const url = `${this.apiUrl}/admin/productos/bulk`;
    const options = {
      headers: this.getHeaders(url),
      body: { ids }
    };
    return this.http.delete(url, options);
  }

  // Productos Mini - Versión ligera para dropdowns
  getProductosMini(search?: string, page: number = 1, limit: number = 100): Observable<any> {
    let url = `${this.apiUrl}/admin/productos/mini`;
    const params: any = { page, limit };

    if (search) {
      params.search = search;
    }

    const queryString = Object.keys(params).map(key => `${key}=${encodeURIComponent(params[key])}`).join('&');
    if (queryString) url += `?${queryString}`;

    return this.http.get(url, { headers: this.getHeaders(url) });
  }

  // Stock
  getStock(params?: any): Observable<any> {
    let url = `${this.apiUrl}/admin/stock`;
    const queryParams: any = {};

    if (params) {
      // Support pagination
      if (params.page) queryParams.page = params.page;
      if (params.page_size) queryParams.page_size = params.page_size;

      // Support filters
      if (params.producto_id) queryParams.producto_id = params.producto_id;
      if (params.search) queryParams.search = params.search;
      if (params.busqueda) queryParams.busqueda = params.busqueda; // Backward compatibility
      if (params.ordenar_por) queryParams.ordenar_por = params.ordenar_por;
      if (params.categoria_id) queryParams.categoria_id = params.categoria_id;
      if (params.talle_nombre) queryParams.talle_nombre = params.talle_nombre;

      // NUEVO: Filtro de stock bajo
      if (params.solo_bajo !== undefined) queryParams.solo_bajo = params.solo_bajo;
      if (params.solo_agotado !== undefined) queryParams.solo_agotado = params.solo_agotado;
      if (params.umbral !== undefined) queryParams.umbral = params.umbral;
    }

    const queryString = Object.keys(queryParams).map(key => `${key}=${encodeURIComponent(queryParams[key])}`).join('&');
    if (queryString) url += `?${queryString}`;

    return this.http.get(url, { headers: this.getHeaders(url) });
  }

  searchProducts(query: string): Observable<any> {
    const url = `${this.apiUrl}/admin/products/search?q=${encodeURIComponent(query)}`;
    return this.http.get(url, { headers: this.getHeaders(url) });
  }



  // Add stock by sizes (increments existing stock)
  addStockBySizes(productId: number, increments: { [size: string]: number }): Observable<any> {
    const url = `${this.apiUrl}/admin/stock/add`;
    return this.http.post(
      url,
      { product_id: productId, increments },
      { headers: this.getHeaders(url) }
    );
  }

  createStock(stock: any): Observable<any> {
    const url = `${this.apiUrl}/admin/stock`;
    return this.http.post(url, stock, { headers: this.getHeaders(url) });
  }

  updateStock(id: number, cantidad: number): Observable<any> {
    const url = `${this.apiUrl}/admin/stock/${id}`;
    return this.http.put(url, { cantidad }, { headers: this.getHeaders(url) });
  }

  deleteStock(id: number): Observable<any> {
    const url = `${this.apiUrl}/admin/stock/${id}`;
    return this.http.delete(url, { headers: this.getHeaders(url) });
  }

  // Imágenes
  uploadImagen(productoId: number, file: File, esPrincipal: boolean = false, orden: number = 0): Observable<any> {
    const formData = new FormData();
    formData.append('imagen', file);
    formData.append('es_principal', esPrincipal.toString());
    formData.append('orden', orden.toString());

    const token = localStorage.getItem('auth_token_admin') || localStorage.getItem('token');
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });

    return this.http.post(`${this.apiUrl}/admin/productos/${productoId}/imagenes`, formData, { headers });
  }

  deleteImagen(id: number): Observable<any> {
    const url = `${this.apiUrl}/admin/imagenes/${id}`;
    return this.http.delete(url, { headers: this.getHeaders(url) });
  }

  updateImagen(id: number, data: any): Observable<any> {
    const url = `${this.apiUrl}/admin/imagenes/${id}`;
    return this.http.put(url, data, { headers: this.getHeaders(url) });
  }

  // Categorías
  getCategorias(incluirSubcategorias: boolean = true, categoriaPadreId?: number, flat: boolean = false): Observable<any> {
    const params = new URLSearchParams();

    params.set('incluir_subcategorias', incluirSubcategorias ? 'true' : 'false');

    if (categoriaPadreId !== undefined && categoriaPadreId !== null) {
      params.set('categoria_padre_id', categoriaPadreId.toString());
    }

    if (flat) {
      params.set('flat', 'true');
    }

    // Agregar ver_todo para admin
    const token = localStorage.getItem('token');
    if (token) {
      params.set('ver_todo', 'true');
    }

    const url = `${this.apiUrl}/categorias?${params.toString()}`;
    return this.http.get(url, { headers: this.getHeaders(url) });
  }

  getCategoriasTree(): Observable<any> {
    const url = `${this.apiUrl}/categorias/tree`;
    return this.http.get(url, { headers: this.getHeaders(url) });
  }

  createCategoria(categoria: any): Observable<any> {
    const url = `${this.apiUrl}/admin/categorias`;
    return this.http.post(url, categoria, { headers: this.getHeaders(url) });
  }

  updateCategoria(id: number, categoria: any): Observable<any> {
    const url = `${this.apiUrl}/admin/categorias/${id}`;
    return this.http.put(url, categoria, { headers: this.getHeaders(url) });
  }

  deleteCategoria(id: number, force: boolean = false): Observable<any> {
    let url = `${this.apiUrl}/admin/categorias/${id}`;
    if (force) {
      url += '?force=true';
    }
    return this.http.delete(url, { headers: this.getHeaders(url) });
  }

  // Métodos genéricos para llamadas HTTP
  get(endpoint: string, params?: any): Observable<any> {
    const url = endpoint.startsWith('http') ? endpoint : `${this.apiUrl}${endpoint}`;
    return this.http.get(url, { headers: this.getHeaders(url), params });
  }

  post(endpoint: string, data: any, params?: any): Observable<any> {
    const url = endpoint.startsWith('http') ? endpoint : `${this.apiUrl}${endpoint}`;
    return this.http.post(url, data, { headers: this.getHeaders(url), params });
  }

  put(endpoint: string, data: any, params?: any): Observable<any> {
    const url = endpoint.startsWith('http') ? endpoint : `${this.apiUrl}${endpoint}`;
    return this.http.put(url, data, { headers: this.getHeaders(url), params });
  }

  delete(endpoint: string, params?: any): Observable<any> {
    const url = endpoint.startsWith('http') ? endpoint : `${this.apiUrl}${endpoint}`;
    return this.http.delete(url, { headers: this.getHeaders(url), params });
  }

  // Talles
  getTalles(): Observable<any> {
    return this.http.get(`${this.apiUrl}/talles`);
  }

  // Colores
  getColores(): Observable<any> {
    return this.http.get(`${this.apiUrl}/colores`);
  }

  createColor(color: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/admin/colores`, color, { headers: this.getHeaders() });
  }

  updateColor(id: number, color: any): Observable<any> {
    return this.http.put(`${this.apiUrl}/admin/colores/${id}`, color, { headers: this.getHeaders() });
  }

  deleteColor(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/admin/colores/${id}`, { headers: this.getHeaders() });
  }

  createTalle(talle: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/admin/talles`, talle, { headers: this.getHeaders() });
  }

  deleteTalle(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/admin/talles/${id}`, { headers: this.getHeaders() });
  }

  // Promociones
  getPromociones(productoId?: number): Observable<any> {
    let url = `${this.apiUrl}/promociones`;
    if (productoId) url += `?producto_id=${productoId}`;
    return this.http.get(url);
  }

  getTiposPromocion(): Observable<any> {
    const url = `${this.apiUrl}/admin/tipos-promocion`;
    return this.http.get(url, { headers: this.getHeaders(url) });
  }

  createPromocion(promocion: any): Observable<any> {
    const url = `${this.apiUrl}/admin/promociones`;
    return this.http.post(url, promocion, { headers: this.getHeaders(url) });
  }

  updatePromocion(id: number, promocion: any): Observable<any> {
    const url = `${this.apiUrl}/admin/promociones/${id}`;
    return this.http.put(url, promocion, { headers: this.getHeaders(url) });
  }

  deletePromocion(id: number): Observable<any> {
    const url = `${this.apiUrl}/admin/promociones/${id}`;
    return this.http.delete(url, { headers: this.getHeaders(url) });
  }

  // Pedidos
  createPedido(pedido: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/pedidos`, pedido);
  }

  getPedidos(estado?: string, page: number = 1, pageSize: number = 20, search?: string): Observable<any> {
    let url = `${this.apiUrl}/admin/pedidos?page=${page}&page_size=${pageSize}`;
    if (estado) url += `&estado=${estado}`;
    if (search) url += `&q=${encodeURIComponent(search)}`;
    return this.http.get(url, { headers: this.getHeaders(url) });
  }

  getPedido(id: number): Observable<any> {
    const url = `${this.apiUrl}/admin/pedidos/${id}`;
    return this.http.get(url, { headers: this.getHeaders(url) });
  }

  updatePedido(id: number, pedido: any): Observable<any> {
    const url = `${this.apiUrl}/admin/pedidos/${id}`;
    return this.http.put(url, pedido, { headers: this.getHeaders(url) });
  }

  aprobarPedido(pedidoId: number): Observable<any> {
    const url = `${this.apiUrl}/admin/pedidos/${pedidoId}/aprobar`;
    return this.http.post(url, {}, { headers: this.getHeaders(url) });
  }

  // Envíos
  calcularEnvio(datos: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/envios/calcular`, datos);
  }

  getPuntosRetiro(carrier: string, codigoPostal: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/envios/puntos-retiro?carrier=${carrier}&codigo_postal=${codigoPostal}`);
  }

  // Métodos de pago
  getMetodosPago(): Observable<any> {
    return this.http.get(`${this.apiUrl}/metodos-pago`);
  }

  // Estadísticas
  getEstadisticas(): Observable<any> {
    const url = `${this.apiUrl}/admin/estadisticas`;
    return this.http.get(url, { headers: this.getHeaders(url) });
  }

  getEstadisticasVentas(periodo: string, semanaOffset?: number, anio?: number, fechaReferencia?: string): Observable<any> {
    let url = `${this.apiUrl}/admin/estadisticas/ventas?periodo=${periodo}`;
    if (semanaOffset !== undefined && semanaOffset !== null) url += `&semana_offset=${semanaOffset}`;
    if (anio) url += `&anio=${anio}`;
    if (fechaReferencia) url += `&fecha_referencia=${fechaReferencia}`;
    return this.http.get(url, { headers: this.getHeaders() });
  }

  // Contacto
  enviarContacto(contacto: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/contacto`, contacto);
  }

  // Clientes
  registrarCliente(cliente: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/clientes`, cliente);
  }

  loginCliente(credenciales: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/clientes/login`, credenciales);
  }

  verificarCodigo(email: string, codigo: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/clientes/verify-code`, { email, codigo });
  }

  reenviarCodigo(email: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/clientes/resend-code`, { email });
  }

  // Ventas Externas
  crearVentaExterna(venta: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/admin/ventas-externas`, venta, { headers: this.getHeaders() });
  }

  getVentasExternas(params?: any): Observable<any> {
    let url = `${this.apiUrl}/admin/ventas-externas`;
    let queryParams = '';
    if (params) {
      const keyValuePairs = Object.keys(params)
        .filter(key => params[key] !== null && params[key] !== undefined && params[key] !== '')
        .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`);
      if (keyValuePairs.length > 0) {
        queryParams = '?' + keyValuePairs.join('&');
      }
    }
    const urlCompleta = `${url}${queryParams}`;
    return this.http.get(urlCompleta, { headers: this.getHeaders(urlCompleta) });
  }

  eliminarVentaExterna(id: number): Observable<any> {
    const url = `${this.apiUrl}/admin/ventas-externas/${id}`;
    return this.http.delete(url, { headers: this.getHeaders(url) });
  }

  getStockByProducto(productoId: number): Observable<any> {
    const url = `${this.apiUrl}/admin/stock?producto_id=${productoId}`;
    return this.http.get(url, { headers: this.getHeaders(url) });
  }

  fixSequences(): Observable<any> {
    const url = `${this.apiUrl}/admin/db/fix-sequences`;
    return this.http.post(url, {}, { headers: this.getHeaders(url) });
  }

  // Newsletter
  subscribeNewsletter(data: { email: string, nombre?: string }): Observable<any> {
    return this.http.post(`${this.apiUrl}/newsletter/subscribe`, data);
  }

  getNewsletterHistory(): Observable<any> {
    const url = `${this.apiUrl}/admin/newsletter/history`;
    return this.http.get(url, { headers: this.getHeaders(url) });
  }

  sendNewsletter(data: { subject: string, content: string, test_email?: string }): Observable<any> {
    const url = `${this.apiUrl}/admin/newsletter/send`;
    return this.http.post(url, data, { headers: this.getHeaders(url) });
  }

  getScheduledNewsletters(): Observable<any> {
    const url = `${this.apiUrl}/admin/newsletter/scheduled`;
    return this.http.get(url, { headers: this.getHeaders(url) });
  }

  scheduleNewsletter(data: any): Observable<any> {
    const url = `${this.apiUrl}/admin/newsletter/schedule`;
    return this.http.post(url, data, { headers: this.getHeaders(url) });
  }

  deleteScheduledNewsletter(id: number): Observable<any> {
    const url = `${this.apiUrl}/admin/newsletter/scheduled/${id}`;
    return this.http.delete(url, { headers: this.getHeaders(url) });
  }

  getNewsletterStats(): Observable<any> {
    const url = `${this.apiUrl}/admin/newsletter/stats`;
    return this.http.get(url, { headers: this.getHeaders(url) });
  }

  // Stock Bulk
  updateStockBulk(data: { product_ids: number[], talle_id: number, cantidad: number }): Observable<any> {
    const url = `${this.apiUrl}/admin/stock/bulk`;
    return this.http.post(url, data, { headers: this.getHeaders(url) });
  }

  // Carrito
  getCart(): Observable<any> {
    const url = `${this.apiUrl}/cart`;
    return this.http.get(url, { headers: this.getHeaders(url) });
  }

  syncCart(items: any[]): Observable<any> {
    const url = `${this.apiUrl}/cart`;
    return this.http.post(url, { items }, { headers: this.getHeaders(url) });
  }

}
