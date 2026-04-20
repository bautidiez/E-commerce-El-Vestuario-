import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router, ActivatedRoute } from '@angular/router';
import { ApiService } from '../../../services/api.service';
import { AuthService } from '../../../services/auth.service';
import Swal from 'sweetalert2';

interface NotaPedido {
  id: number;
  pedido_id: number;
  admin_id: number;
  admin_username: string;
  contenido: string;
  created_at: string;
}

interface Pedido {
  id: number;
  numero_pedido: string;
  cliente_nombre: string;
  cliente_email: string;
  cliente_telefono?: string;
  cliente_direccion: string;
  cliente_codigo_postal: string;
  cliente_localidad: string;
  cliente_provincia: string;
  estado: string;
  subtotal: number;
  descuento: number;
  costo_envio: number;
  total: number;
  aprobado: boolean;
  fecha_expiracion?: string;
  fecha_aprobacion?: string;
  admin_aprobador_id?: number;
  admin_aprobador_username?: string;
  created_at: string;
  updated_at: string;
  items: any[];
  notas?: string; // notas legacy (campo texto)
}

@Component({
  selector: 'app-pedidos-admin',
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './pedidos-admin.html',
  styleUrl: './pedidos-admin.css'
})
export class PedidosAdminComponent implements OnInit {
  pedidos: Pedido[] = [];
  pedidoSeleccionado: Pedido | null = null;
  loading = true;

  // Filtros
  filtroEstado = '';
  busquedaCliente = '';
  estados = ['pendiente_aprobacion', 'confirmado', 'en_preparacion', 'enviado', 'entregado', 'cancelado'];

  // Estado del pedido
  nuevoEstado = '';

  // Sistema de notas internas
  notasInternas: NotaPedido[] = [];
  nuevaNota = '';
  loadingNotas = false;

  // Paginación
  currentPage = 1;
  pageSize = 40;
  totalPages = 1;
  totalOrders = 0;
  pagesArray: number[] = [];

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private cdr: ChangeDetectorRef
  ) { }

  ngOnInit() {
    if (!this.authService.isLoggedIn()) {
      this.router.navigate(['/admin/login']);
      return;
    }
    this.currentPage = 1;
    this.loadPedidos();
  }

  loadPedidos() {
    this.loading = true;
    this.apiService.getPedidos(this.filtroEstado || undefined, this.currentPage, this.pageSize, this.busquedaCliente || undefined).subscribe({
      next: (response: any) => {
        // Handle paginated response
        if (response.items) {
          this.pedidos = response.items;
          this.totalOrders = response.total;
          this.totalPages = response.pages;
          this.currentPage = response.page;
          this.generatePagesArray();
        } else {
          // Fallback if backend implementation varies
          this.pedidos = response;
          this.totalOrders = response.length;
          this.totalPages = 1;
        }
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (error: any) => {
        console.error('Error cargando pedidos:', error);
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  generatePagesArray() {
    this.pagesArray = [];
    const maxVisible = 5;
    let start = Math.max(1, this.currentPage - 2);
    let end = Math.min(this.totalPages, start + maxVisible - 1);

    if (end - start < maxVisible - 1) {
      start = Math.max(1, end - maxVisible + 1);
    }

    for (let i = start; i <= end; i++) {
      this.pagesArray.push(i);
    }
  }

  cambiarPagina(page: number) {
    if (page < 1 || page > this.totalPages || page === this.currentPage) return;
    this.currentPage = page;
    this.loadPedidos();
  }

  siguientePagina() {
    if (this.currentPage < this.totalPages) {
      this.cambiarPagina(this.currentPage + 1);
    } else {
      Swal.fire({
        toast: true,
        position: 'top-end',
        icon: 'info',
        title: 'No hay más páginas',
        showConfirmButton: false,
        timer: 1500
      });
    }
  }

  anteriorPagina() {
    if (this.currentPage > 1) {
      this.cambiarPagina(this.currentPage - 1);
    }
  }

  // Removed pedidosFiltrados getter in favor of server-side filtering
  get pedidosFiltrados(): Pedido[] {
    return this.pedidos;
  }

  filtrarPorEstado() {
    this.currentPage = 1;
    this.loadPedidos();
  }

  buscar() {
    this.currentPage = 1;
    this.loadPedidos();
  }

  limpiarFiltros() {
    this.filtroEstado = '';
    this.busquedaCliente = '';
    this.currentPage = 1;
    this.loadPedidos();
  }

  verDetalle(pedido: Pedido) {
    this.apiService.getPedido(pedido.id).subscribe({
      next: (data: Pedido) => {
        this.pedidoSeleccionado = data;
        this.nuevoEstado = data.estado;
        this.loadNotasInternas(pedido.id);
        this.cdr.detectChanges();
      },
      error: (error: any) => {
        console.error('Error cargando detalle:', error);
        Swal.fire('Error', 'No se pudo cargar el detalle del pedido', 'error');
        this.cdr.detectChanges();
      }
    });
  }

  loadNotasInternas(pedidoId: number) {
    this.loadingNotas = true;
    this.apiService.get(`/admin/pedidos/${pedidoId}/notas`).subscribe({
      next: (notas: NotaPedido[]) => {
        this.notasInternas = notas;
        this.loadingNotas = false;
        this.cdr.detectChanges();
      },
      error: (error: any) => {
        console.error('Error cargando notas:', error);
        this.loadingNotas = false;
        this.cdr.detectChanges();
      }
    });
  }

  agregarNota() {
    if (!this.pedidoSeleccionado || !this.nuevaNota.trim()) {
      return;
    }

    this.apiService.post(`/admin/pedidos/${this.pedidoSeleccionado.id}/notas`, {
      contenido: this.nuevaNota
    }).subscribe({
      next: (nota: NotaPedido) => {
        this.notasInternas.unshift(nota);
        this.nuevaNota = '';
        Swal.fire({
          toast: true,
          position: 'top-end',
          icon: 'success',
          title: 'Nota agregada',
          showConfirmButton: false,
          timer: 1500
        });
      },
      error: (error: any) => {
        console.error('Error agregando nota:', error);
        Swal.fire('Error', 'No se pudo agregar la nota', 'error');
      }
    });
  }

  async eliminarNota(notaId: number) {
    const result = await Swal.fire({
      title: '¿Eliminar esta nota?',
      text: 'Esta acción no se puede deshacer',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    });

    if (!result.isConfirmed) return;

    this.apiService.delete(`/admin/notas/${notaId}`).subscribe({
      next: () => {
        this.notasInternas = this.notasInternas.filter(n => n.id !== notaId);
        Swal.fire({
          toast: true,
          position: 'top-end',
          icon: 'success',
          title: 'Nota eliminada',
          showConfirmButton: false,
          timer: 1500
        });
      },
      error: (error: any) => {
        console.error('Error eliminando nota:', error);
        Swal.fire('Error', 'No se pudo eliminar la nota', 'error');
      }
    });
  }

  actualizarEstado() {
    if (!this.pedidoSeleccionado) return;

    const actualizacion = {
      estado: this.nuevoEstado
    };

    this.apiService.updatePedido(this.pedidoSeleccionado.id, actualizacion).subscribe({
      next: () => {
        Swal.fire({
          toast: true,
          position: 'top-end',
          icon: 'success',
          title: 'Estado actualizado',
          showConfirmButton: false,
          timer: 2000
        });
        this.loadPedidos();
        if (this.pedidoSeleccionado) {
          this.pedidoSeleccionado.estado = this.nuevoEstado;
        }
      },
      error: (error: any) => {
        Swal.fire('Error', 'No se pudo actualizar el estado', 'error');
        console.error(error);
      }
    });
  }

  cerrarDetalle() {
    this.pedidoSeleccionado = null;
    this.notasInternas = [];
    this.nuevaNota = '';
  }

  async aprobarPedido(pedido: Pedido) {
    const result = await Swal.fire({
      title: '¿Aprobar pedido?',
      text: `Se aprobará el pedido ${pedido.numero_pedido}. Esto reducirá el stock y procesará la orden.`,
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'Sí, aprobar',
      cancelButtonText: 'Cancelar'
    });

    if (!result.isConfirmed) return;

    this.apiService.aprobarPedido(pedido.id).subscribe({
      next: (response: any) => {
        Swal.fire('¡Éxito!', response.message, 'success');
        this.loadPedidos();
        if (this.pedidoSeleccionado && this.pedidoSeleccionado.id === pedido.id) {
          this.pedidoSeleccionado = response.pedido;
        }
        this.cdr.detectChanges();
      },
      error: (error: any) => {
        Swal.fire('Error', error.error?.error || 'No se pudo aprobar el pedido', 'error');
        console.error(error);
      }
    });
  }

  async cancelarPedido(pedido: Pedido) {
    const result = await Swal.fire({
      title: '¿Cancelar pedido?',
      text: `Se cancelará el pedido ${pedido.numero_pedido}. El cliente verá este pedido como "Cancelado". Esta acción NO se puede deshacer.`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      confirmButtonText: 'Sí, cancelar pedido',
      cancelButtonText: 'Volver'
    });

    if (!result.isConfirmed) return;

    this.apiService.updatePedido(pedido.id, { estado: 'cancelado' }).subscribe({
      next: () => {
        Swal.fire('Cancelado', 'El pedido ha sido cancelado exitosamente', 'success');
        this.loadPedidos();
        if (this.pedidoSeleccionado && this.pedidoSeleccionado.id === pedido.id) {
          this.pedidoSeleccionado.estado = 'cancelado';
        }
        this.cdr.detectChanges();
      },
      error: (error: any) => {
        Swal.fire('Error', error.error?.error || 'No se pudo cancelar el pedido', 'error');
        console.error(error);
      }
    });
  }

  getDiasRestantes(fecha_expiracion: string): number {
    if (!fecha_expiracion) return 0;
    const ahora = new Date().getTime();
    const expira = new Date(fecha_expiracion).getTime();
    const diff = expira - ahora;
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  }

  isExpirando(pedido: Pedido): boolean {
    if (!pedido.fecha_expiracion || pedido.aprobado) return false;
    return this.getDiasRestantes(pedido.fecha_expiracion) <= 2;
  }

  getEstadoClass(estado: string): string {
    const clases: any = {
      'pendiente': 'estado-pendiente',
      'pendiente_aprobacion': 'estado-pendiente-aprobacion',
      'confirmado': 'estado-confirmado',
      'en_preparacion': 'estado-preparacion',
      'enviado': 'estado-enviado',
      'entregado': 'estado-entregado',
      'cancelado': 'estado-cancelado'
    };
    return clases[estado] || '';
  }

  getEstadoLabel(estado: string): string {
    const labels: any = {
      'pendiente': 'Pendiente',
      'pendiente_aprobacion': 'Pendiente de Aprobación',
      'confirmado': 'Confirmado',
      'en_preparacion': 'En Preparación',
      'enviado': 'Enviado',
      'entregado': 'Entregado',
      'cancelado': 'Cancelado'
    };
    return labels[estado] || estado;
  }

  formatFecha(fecha: string): string {
    if (!fecha) return '-';
    const d = new Date(fecha);
    return d.toLocaleDateString('es-AR') + ' ' + d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
  }

  getTotalItems(pedido: Pedido): number {
    return pedido.items?.reduce((sum, item) => sum + item.cantidad, 0) || 0;
  }
}
