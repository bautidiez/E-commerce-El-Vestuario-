import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import Swal from 'sweetalert2';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-home',
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './home.html',
  styleUrl: './home.css'
})
export class HomeComponent implements OnInit {
  productosDestacados: any[] = [];
  productosOfertas: any[] = [];
  categorias: any[] = [];
  loading = true;
  newsletterNombre = '';
  newsletterEmail = '';

  constructor(
    private apiService: ApiService,
    private cdr: ChangeDetectorRef
  ) { }

  ngOnInit() {
    this.loadProductosDestacados();
    this.loadProductosOfertas();
    this.loadCategorias();
  }

  loadProductosDestacados() {
    this.apiService.getProductos({ destacados: true }).subscribe({
      next: (data) => {
        const productos = data.items || data;
        this.productosDestacados = productos.slice(0, 9);
        this.checkAllLoaded();
      },
      error: (error) => {
        console.error('Error cargando productos destacados:', error);
        this.checkAllLoaded();
      }
    });
  }

  loadProductosOfertas() {
    this.apiService.getProductos({ ofertas: true }).subscribe({
      next: (data) => {
        const productos = data.items || data;
        this.productosOfertas = productos.slice(0, 9);
        this.checkAllLoaded();
      },
      error: (error) => {
        console.error('Error cargando productos en oferta:', error);
        this.productosOfertas = [];
        this.checkAllLoaded();
      }
    });
  }

  loadCategorias() {
    this.apiService.getCategorias().subscribe({
      next: (data) => {
        this.categorias = data.filter((cat: any) => !cat.categoria_padre_id);
        this.checkAllLoaded();
      },
      error: (error) => {
        console.error('Error cargando categorías:', error);
        this.checkAllLoaded();
      }
    });
  }

  private loadCount = 0;
  private checkAllLoaded() {
    this.loadCount++;
    if (this.loadCount >= 3) {
      this.loading = false;
      this.cdr.detectChanges();
    }
  }

  getImagenPrincipal(producto: any): string {
    const apiBase = this.apiService.getApiUrl().replace('/api', '');
    if (producto.imagenes && producto.imagenes.length > 0) {
      const principal = producto.imagenes.find((img: any) => img.es_principal);
      if (principal) {
        return `${apiBase}${principal.url}`;
      }
      return `${apiBase}${producto.imagenes[0].url}`;
    }
    return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Crect fill='%23ddd' width='300' height='300'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' font-family='sans-serif' font-size='18' fill='%23999'%3ESin imagen%3C/text%3E%3C/svg%3E";
  }

  // Calcular precio con 15% descuento por transferencia
  getPrecioTransferencia(producto: any): number {
    return this.getPrecioFinal(producto) * 0.85; // 15% descuento sobre el mejor precio
  }

  // Calcular cuota (dividir en 3 cuotas sin interés)
  getCuota(producto: any): number {
    return this.getPrecioFinal(producto) / 3;
  }

  // Obtener el mejor precio disponible (base, descuento directo o promoción)
  getPrecioFinal(producto: any): number {
    let mejorPrecio = producto.precio_descuento || producto.precio_base;

    if (producto.promociones && producto.promociones.length > 0) {
      const promo = producto.promociones[0];
      const tipo = (promo.tipo_promocion_nombre || '').toLowerCase();
      const valor = promo.valor || 0;

      if (tipo.includes('porcentaje')) {
        const precioPromo = producto.precio_base * (1 - (valor / 100));
        if (precioPromo < mejorPrecio) mejorPrecio = precioPromo;
      } else if (tipo.includes('fijo')) {
        const precioPromo = Math.max(0, producto.precio_base - valor);
        if (precioPromo < mejorPrecio) mejorPrecio = precioPromo;
      }
    }

    return mejorPrecio;
  }

  // Verificar si un producto tiene oferta válida
  tieneOferta(producto: any): boolean {
    return (producto.precio_descuento && producto.precio_descuento > 0) ||
      (producto.promociones && producto.promociones.some((p: any) => p.esta_activa));
  }

  // Calcular porcentaje de descuento
  getPorcentajeDescuento(producto: any): number {
    const precioBase = producto.precio_base;
    const precioFinal = this.getPrecioFinal(producto);

    if (!precioBase || precioFinal >= precioBase) return 0;
    return Math.round((1 - (precioFinal / precioBase)) * 100);
  }

  // Getter para controlar la visibilidad de la sección de ofertas
  get mostrarSeccionOfertas(): boolean {
    return this.productosOfertas.length > 0;
  }

  // Obtener texto para el badge de promoción
  getBadgeText(producto: any): string {
    if (!producto.promociones || producto.promociones.length === 0) return '';
    const promo = producto.promociones[0];
    const tipo = (promo.tipo_promocion_nombre || '').toLowerCase();

    if (tipo.includes('porcentaje')) return `${promo.valor}% OFF`;
    if (tipo.includes('fijo')) return `$${promo.valor} OFF`;
    if (tipo.includes('2x1')) return '2x1';
    if (tipo.includes('3x2')) return '3x2';

    return promo.tipo_promocion_nombre;
  }

  suscribirNewsletter() {
    // Por ahora solo muestra un mensaje, se puede implementar backend después
    Swal.fire({
      icon: 'success',
      title: '¡Suscripción exitosa!',
      text: '¡Gracias por suscribirte! Te mantendremos informado de nuestras novedades.',
      confirmButtonColor: '#000000',
      confirmButtonText: 'Aceptar'
    });
    this.newsletterNombre = '';
    this.newsletterEmail = '';
  }
}
