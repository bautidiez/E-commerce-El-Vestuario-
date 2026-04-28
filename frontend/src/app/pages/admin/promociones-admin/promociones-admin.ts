import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { ApiService } from '../../../services/api.service';
import { AuthService } from '../../../services/auth.service';
import Swal from 'sweetalert2';

interface Promocion {
  id: number;
  alcance: 'producto' | 'categoria' | 'tienda';
  productos_ids: number[];
  productos_nombres?: string[];
  categorias_ids: number[];
  categorias_nombres?: string[];
  tipo_promocion_id: number;
  tipo_nombre?: string;
  valor: number;
  activa: boolean;
  fecha_inicio: string;
  fecha_fin: string | null;
  estado?: 'activa' | 'programada' | 'expirada';
  es_cupon?: boolean;
  codigo?: string;
  envio_gratis?: boolean;
}

@Component({
  selector: 'app-promociones-admin',
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './promociones-admin.html',
  styleUrl: './promociones-admin.css'
})
export class PromocionesAdminComponent implements OnInit {
  promociones: Promocion[] = [];
  tiposPromocion: any[] = [];
  productos: any[] = [];
  categorias: any[] = [];
  loading = true;

  // Autocomplete
  searchQuery = '';
  searchResults: any[] = [];
  searching = false;
  productosSeleccionados: any[] = [];
  categoriasSeleccionadas: number[] = [];

  // Wizard
  mostrarWizard = false;
  pasoActual = 1;
  totalPasos = 2;

  nuevaPromocion: any = {
    alcance: 'producto',
    productos_ids: [],
    categorias_ids: [],
    tipo_promocion_id: null,
    valor: null,
    activa: true,
    fecha_inicio: '',
    fecha_fin: '',
    sin_fecha_fin: false,
    es_cupon: false,
    codigo: '',
    envio_gratis: false
  };

  modoEdicion = false;
  promocionEditando: any = null;

  // Filtros
  filtroEstado: 'todas' | 'activas' | 'programadas' | 'expiradas' = 'todas';
  busqueda = '';

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) { }

  ngOnInit() {
    if (!this.authService.isLoggedIn()) {
      this.router.navigate(['/admin/login']);
      return;
    }
    this.loadPromociones();
    this.loadTiposPromocion();
    this.loadProductos();
    this.loadCategorias();
  }

  loadPromociones() {
    if (this.promociones.length === 0) {
      this.loading = true;
    }

    this.apiService.get('/admin/promociones').subscribe({
      next: (data: Promocion[]) => {
        this.promociones = data.map(p => ({
          ...p,
          estado: this.getEstadoPromocion(p.fecha_inicio, p.fecha_fin, p.activa)
        }));
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (error: any) => {
        console.error('Error cargando promociones:', error);
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  get promocionesFiltradas(): Promocion[] {
    let filtradas = this.promociones;

    // Filtro por estado
    if (this.filtroEstado !== 'todas') {
      const estadoMap: any = {
        'activas': 'activa',
        'programadas': 'programada',
        'expiradas': 'expirada'
      };
      const estadoBuscado = estadoMap[this.filtroEstado];
      filtradas = filtradas.filter(p => p.estado === estadoBuscado);
    }

    // Búsqueda
    if (this.busqueda.trim()) {
      const termino = this.busqueda.toLowerCase();
      filtradas = filtradas.filter(p =>
        (p.productos_nombres || []).some(n => n.toLowerCase().includes(termino)) ||
        (p.categorias_nombres || []).some(n => n.toLowerCase().includes(termino)) ||
        (p.tipo_nombre || '').toLowerCase().includes(termino)
      );
    }

    return filtradas;
  }

  get stats() {
    return {
      activas: this.promociones.filter(p => p.estado === 'activa').length,
      programadas: this.promociones.filter(p => p.estado === 'programada').length,
      expiradas: this.promociones.filter(p => p.estado === 'expirada').length
    };
  }

  loadTiposPromocion() {
    this.apiService.getTiposPromocion().subscribe({
      next: (data: any) => {
        console.log('DEBUG: Tipos de promoción recibidos:', data);
        console.log('DEBUG: Cantidad de tipos:', data?.length);
        this.tiposPromocion = data;
        
        if (!data || data.length === 0) {
          console.warn('DEBUG: La lista de tipos de promoción está VACÍA');
        }
      },
      error: (error: any) => {
        console.error('DEBUG: Error cargando tipos de promoción:', error);
        Swal.fire({
          title: 'Error de Conexión',
          text: `No se pudieron cargar los tipos de promoción. Status: ${error.status} - ${error.message}`,
          icon: 'error'
        });
      }
    });
  }

  loadProductos() {
    this.apiService.getProductos().subscribe({
      next: (data: any) => {
        this.productos = data.items || data;
      },
      error: (error: any) => {
        console.error('Error cargando productos:', error);
      }
    });
  }

  loadCategorias() {
    this.apiService.getCategoriasTree().subscribe({
      next: (data: any[]) => {
        console.log('DEBUG: Árbol de categorías para promociones:', data);
        if (!data || data.length === 0) {
          console.warn('DEBUG: No se recibieron categorías');
        }
        this.categorias = data;
        this.cdr.detectChanges();
      },
      error: (error: any) => {
        console.error('Error cargando árbol de categorías:', error);
        // Fallback: tratar de cargar plano si el árbol falla
        this.apiService.getCategorias(true, undefined, true).subscribe(data => {
            if (data) {
                this.categorias = data;
                this.cdr.detectChanges();
            }
        });
      }
    });
  }

  nuevo() {
    this.modoEdicion = false;
    this.promocionEditando = null;
    const hoy = new Date();
    const fin = new Date();
    fin.setMonth(fin.getMonth() + 1);

    this.nuevaPromocion = {
      alcance: 'producto',
      productos_ids: [],
      categorias_ids: [],
      tipo_promocion_id: null,
      valor: null,
      activa: true,
      fecha_inicio: hoy.toISOString().split('T')[0],
      fecha_fin: fin.toISOString().split('T')[0],
      sin_fecha_fin: false,
      es_cupon: false,
      codigo: '',
      envio_gratis: false
    };
    this.productosSeleccionados = [];
    this.categoriasSeleccionadas = [];
    this.searchQuery = '';
    this.pasoActual = 1;
    this.mostrarWizard = true;
  }

  editar(promocion: Promocion) {
    this.modoEdicion = true;
    this.promocionEditando = promocion;
    this.nuevaPromocion = {
      alcance: promocion.alcance || 'producto',
      productos_ids: promocion.productos_ids || [],
      categorias_ids: promocion.categorias_ids || [],
      tipo_promocion_id: promocion.tipo_promocion_id,
      valor: promocion.valor,
      activa: promocion.activa,
      fecha_inicio: promocion.fecha_inicio.split('T')[0],
      fecha_fin: promocion.fecha_fin ? promocion.fecha_fin.split('T')[0] : '',
      sin_fecha_fin: !promocion.fecha_fin,
      es_cupon: promocion.es_cupon || false,
      codigo: promocion.codigo || '',
      envio_gratis: promocion.envio_gratis || false
    };

    // Cargar visualmente productos seleccionados
    if (this.nuevaPromocion.productos_ids.length > 0) {
      if (promocion.productos_nombres && promocion.productos_nombres.length === promocion.productos_ids.length) {
        // Usar los nombres que vienen de la promoción (más seguro que filtrar productos paginados)
        this.productosSeleccionados = promocion.productos_ids.map((id, index) => ({
          id: id,
          nombre: promocion.productos_nombres![index]
        }));
      } else {
        // Fallback: tratar de encontrar en la lista cargada
        this.productosSeleccionados = this.productos.filter(p => this.nuevaPromocion.productos_ids.includes(p.id));
      }
    } else {
      this.productosSeleccionados = [];
    }
    this.categoriasSeleccionadas = [...this.nuevaPromocion.categorias_ids];
    this.pasoActual = 1;
    this.mostrarWizard = true;
  }

  siguientePaso() {
    if (this.pasoActual === 1) {
      if (this.nuevaPromocion.alcance === 'producto' && this.productosSeleccionados.length === 0) {
        Swal.fire({ title: 'Requerido', text: 'Por favor selecciona al menos un producto', icon: 'warning' });
        return;
      }
      if (this.nuevaPromocion.alcance === 'categoria' && this.categoriasSeleccionadas.length === 0) {
        Swal.fire({ title: 'Requerido', text: 'Por favor selecciona al menos una categoría', icon: 'warning' });
        return;
      }
      if (!this.nuevaPromocion.tipo_promocion_id && !this.nuevaPromocion.envio_gratis) {
        Swal.fire({ title: 'Requerido', text: 'Por favor selecciona el tipo de promoción o activa Envío Gratis', icon: 'warning' });
        return;
      }
      if (this.mostrarCampoValor() && !this.nuevaPromocion.valor) {
        Swal.fire({ title: 'Requerido', text: 'Por favor ingresa el valor de la promoción', icon: 'warning' });
        return;
      }
      if (this.nuevaPromocion.es_cupon && !this.nuevaPromocion.codigo) {
        Swal.fire({ title: 'Requerido', text: 'Por favor ingresa el código del cupón', icon: 'warning' });
        return;
      }
    }
    if (this.pasoActual < this.totalPasos) {
      this.pasoActual++;
    }
  }

  pasoAnterior() {
    if (this.pasoActual > 1) {
      this.pasoActual--;
    }
  }

  guardar() {
    if (!this.validarFechas()) {
      Swal.fire({ title: 'Fechas Inválidas', text: 'La fecha de fin debe ser posterior a la fecha de inicio', icon: 'error' });
      return;
    }

    // Asegurar IDs antes de enviar
    this.nuevaPromocion.productos_ids = this.productosSeleccionados.map(p => p.id);
    this.nuevaPromocion.categorias_ids = this.categoriasSeleccionadas;

    const promocionData = {
      ...this.nuevaPromocion,
      valor: this.nuevaPromocion.valor || 0,
      fecha_inicio: new Date(this.nuevaPromocion.fecha_inicio + 'T00:00:00.000Z').toISOString(),
      fecha_fin: this.nuevaPromocion.sin_fecha_fin ? null : new Date(this.nuevaPromocion.fecha_fin + 'T23:59:59.999Z').toISOString()
    };

    const request = this.modoEdicion
      ? this.apiService.updatePromocion(this.promocionEditando!.id, promocionData)
      : this.apiService.createPromocion(promocionData);

    request.subscribe({
      next: () => {
        Swal.fire({
          title: this.modoEdicion ? 'Actualizado' : 'Creado',
          text: this.modoEdicion ? 'Promoción actualizada correctamente' : 'Promoción creada exitosamente',
          icon: 'success',
          timer: 2000,
          showConfirmButton: false
        });
        this.loadPromociones();
        this.cancelar();
      },
      error: (error: any) => {
        const errorMsg = error.error?.error || 'Error desconocido';
        Swal.fire('Error', 'Error al guardar promoción: ' + errorMsg, 'error');
        console.error(error);
      }
    });
  }

  eliminar(promocionId: number) {
    Swal.fire({
      title: '¿Estás seguro?',
      text: "Esta acción no se puede deshacer",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#2563eb',
      cancelButtonColor: '#64748b',
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    }).then((result) => {
      if (result.isConfirmed) {
        this.apiService.deletePromocion(promocionId).subscribe({
          next: () => {
            this.loadPromociones();
            Swal.fire('Eliminado', 'La promoción ha sido eliminada', 'success');
          },
          error: (error: any) => {
            Swal.fire('Error', 'No se pudo eliminar la promoción', 'error');
            console.error(error);
          }
        });
      }
    });
  }

  cancelar() {
    this.mostrarWizard = false;
    this.modoEdicion = false;
    this.promocionEditando = null;
    this.pasoActual = 1;
  }

  // Helpers
  getEstadoPromocion(inicio: string, fin: string | null, activa: boolean): 'activa' | 'programada' | 'expirada' {
    if (!activa) return 'expirada';

    const ahora = new Date();
    const fechaInicio = new Date(inicio);
    
    if (ahora < fechaInicio) return 'programada';
    
    if (fin) {
      const fechaFin = new Date(fin);
      if (ahora > fechaFin) return 'expirada';
    }
    
    return 'activa';
  }

  getEstadoClass(estado: string): string {
    return `badge-${estado}`;
  }

  getEstadoLabel(estado: string): string {
    const labels: any = {
      'activa': 'Activa',
      'programada': 'Programada',
      'expirada': 'Expirada'
    };
    return labels[estado] || estado;
  }

  getTipoPromocionNombre(tipoId: number): string {
    const tipo = this.tiposPromocion.find(t => t.id === tipoId);
    if (!tipo) return 'N/A';
    return tipo.descripcion || (tipo.nombre ? tipo.nombre.toUpperCase() : 'N/A');
  }

  getTipoSeleccionado(): any {
    if (!this.nuevaPromocion.tipo_promocion_id) return null;
    return this.tiposPromocion.find(t => t.id === this.nuevaPromocion.tipo_promocion_id);
  }

  mostrarCampoValor(): boolean {
    const tipo = this.getTipoSeleccionado();
    if (!tipo) return false;
    // Si es envío gratis, no se necesita valor (se aplica automáticamente al alcance seleccionado)
    if (this.nuevaPromocion.envio_gratis) return false;
    return tipo.nombre === 'descuento_porcentaje' || tipo.nombre === 'descuento_fijo';
  }

  getPlaceholderValor(): string {
    const tipo = this.getTipoSeleccionado();
    if (!tipo) return '';
    if (tipo.nombre === 'descuento_porcentaje') return 'Ej: 20 para 20%';
    if (tipo.nombre === 'descuento_fijo') return 'Ej: 2000 para $2000';
    return '';
  }

  validarFechas(): boolean {
    if (this.nuevaPromocion.sin_fecha_fin) return true;
    const inicio = new Date(this.nuevaPromocion.fecha_inicio);
    const fin = new Date(this.nuevaPromocion.fecha_fin);
    return fin > inicio;
  }

  formatFecha(fecha: string | null): string {
    if (!fecha) return 'Indefinida';
    // Si la fecha viene como "YYYY-MM-DD", la procesamos como local
    if (fecha.includes('-') && !fecha.includes('T')) {
      const [year, month, day] = fecha.split('-').map(Number);
      return new Date(year, month - 1, day).toLocaleDateString('es-AR');
    }
    return new Date(fecha).toLocaleDateString('es-AR');
  }

  getProductoNombre(productoId: number | null): string {
    if (!productoId) return '-';
    const producto = this.productos.find(p => p.id === productoId);
    return producto ? producto.nombre : '-';
  }

  getDiasRestantes(fechaFin: string | null): string {
    if (!fechaFin) return '∞';
    const ahora = new Date();
    const fin = new Date(fechaFin);
    const diff = fin.getTime() - ahora.getTime();
    if (diff < 0) return '0';
    return Math.ceil(diff / (1000 * 60 * 60 * 24)).toString();
  }

  // Autocomplete Products
  onSearchInput() {
    if (this.searchQuery.length < 2) {
      this.searchResults = [];
      return;
    }

    this.searching = true;
    this.apiService.searchProducts(this.searchQuery).subscribe({
      next: (results) => {
        // Filtrar productos que ya están seleccionados
        this.searchResults = results.filter((p: any) =>
          !this.productosSeleccionados.some(sel => sel.id === p.id)
        );
        this.searching = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.searching = false;
        this.searchResults = [];
        this.cdr.detectChanges();
      }
    });
  }

  addProducto(product: any) {
    if (!this.productosSeleccionados.some(p => p.id === product.id)) {
      this.productosSeleccionados.push(product);
    }
    this.searchQuery = '';
    this.searchResults = [];
  }

  removeProducto(productId: number) {
    this.productosSeleccionados = this.productosSeleccionados.filter(p => p.id !== productId);
  }

  // Categories
  toggleCategoria(catId: number) {
    const index = this.categoriasSeleccionadas.indexOf(catId);
    if (index > -1) {
      this.categoriasSeleccionadas.splice(index, 1);
    } else {
      this.categoriasSeleccionadas.push(catId);
    }
  }

  isCategoriaSelected(catId: number): boolean {
    return this.categoriasSeleccionadas.includes(catId);
  }

  getCleanCategoryPath(catId: number | null, pathNodes: number[] = []): string {
    if (!catId) return '';

    // Evitar recursión infinita
    if (pathNodes.includes(catId)) {
      return '';
    }

    const cat = this.categorias.find(c => Number(c.id) === Number(catId));
    if (!cat) return '';

    if (!cat.categoria_padre_id) {
      return cat.nombre;
    }

    const padre = this.categorias.find(p => Number(p.id) === Number(cat.categoria_padre_id));
    if (padre && padre.id !== catId) {
      return `${this.getCleanCategoryPath(padre.id, [...pathNodes, catId])} > ${cat.nombre}`;
    }

    return cat.nombre;
  }

  getCategoryLabel(catId: number): string {
    // Si la lista es un árbol, necesitamos buscar recursivamente para el resumen
    const findInTree = (nodes: any[], id: number): any => {
      for (const node of nodes) {
        if (node.id === id) return node;
        if (node.subcategorias && node.subcategorias.length > 0) {
          const found = findInTree(node.subcategorias, id);
          if (found) return found;
        }
      }
      return null;
    };

    const cat = findInTree(this.categorias, catId);
    return cat ? cat.nombre : `Cat #${catId}`;
  }

  getAlcanceResumen(): string {
    const a = this.nuevaPromocion.alcance;
    if (a === 'tienda') return 'Toda la tienda';
    if (a === 'producto') return `${this.productosSeleccionados.length} producto(s)`;
    if (a === 'categoria') return `${this.categoriasSeleccionadas.length} categoría(s)`;
    return '-';
  }
}
