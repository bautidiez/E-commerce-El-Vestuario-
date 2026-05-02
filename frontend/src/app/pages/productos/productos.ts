import { Component, OnInit, OnDestroy, ChangeDetectorRef, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { ProductoService } from '../../services/producto.service';
import { LazyLoadDirective } from '../../directives/image-lazy.directive';
import { Observable, Subject, of, merge, forkJoin } from 'rxjs';
import { takeUntil, map, catchError, tap } from 'rxjs/operators';

@Component({
  selector: 'app-productos',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, LazyLoadDirective],
  templateUrl: './productos.html',
  styleUrl: './productos.css',
  changeDetection: ChangeDetectionStrategy.OnPush  // ⚡ ULTRA PERFORMANCE: OnPush activated
})
export class ProductosComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  productos: any[] = [];
  categorias: any[] = [];
  talles: any[] = [];
  
  loading = true;
  loadingMore = false;
  showNoProducts = false; // ⚡ Nuevo: Controlar delay del mensaje vacío

  // Paginación
  currentPage = 1;
  pageSize = 20;
  totalProducts = 0;
  hasMoreProducts = false;

  // Título y filtros
  tituloActual = 'PRODUCTOS';
  currentCategoryLevel: number = 0;
  parentCategory: any = null;
  currentCategory: any = null;
  busqueda = '';

  filtros = {
    categoria_id: null as number | null,
    destacados: false,
    color: '',
    talle_id: null as number | null,
    dorsal: '',
    numero: null as number | null,
    version: '',
    precio_min: null as number | null,
    precio_max: null as number | null,
    ordenar_por: 'destacado' as string
  };

  coloresDisponibles: string[] = [];
  dorsalesDisponibles: string[] = [];
  numerosDisponibles: number[] = [];
  versionesDisponibles: string[] = ['Hincha', 'Jugador'];

  mostrarFiltros = false;
  precioMinInput = '';
  precioMaxInput = '';
  categoriesMap = new Map<number, any>();
  private categorySlugMap: { [key: string]: number } = {};
  private categoryIdToSlug: { [key: number]: string } = {};

  constructor(
    private apiService: ApiService,
    private productoService: ProductoService,
    private route: ActivatedRoute,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) { }

  ngOnInit() {
    console.log('🚀 [ProductosComponent] ngOnInit INICIADO');

    // ⚡ CARGAR CATEGORÍAS Y TALLES EN PARALELO (no secuencial)
    forkJoin({
      categorias: this.loadCategorias(),
      talles: this.loadTalles()
    }).subscribe({
      next: () => {
        console.log('✅ Categorías y Talles cargados EN PARALELO');
        
        // Ahora sí, cargar productos según la ruta
        this.handleRouteParams();
        
        // Escuchar cambios de ruta
        merge(this.route.params, this.route.queryParams)
          .pipe(takeUntil(this.destroy$))
          .subscribe(() => {
            console.log('🔄 Route params/queryParams CHANGED');
            this.handleRouteParams();
          });
      },
      error: (err) => {
        console.error('❌ Error setup inicial:', err);
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private handleRouteParams() {
    console.log('📍 Manejando parámetros de ruta');
    
    const params = this.route.snapshot.params;
    const queryParams = this.route.snapshot.queryParams;

    if (queryParams['busqueda']) {
      this.busqueda = queryParams['busqueda'];
    }
    if (queryParams['ofertas'] === 'true') {
      this.filtros.destacados = false;
    }

    const slug = params['slug'];
    if (slug) {
      const decodedSlug = decodeURIComponent(slug);
      const categoryId = this.getCategoryIdFromSlug(decodedSlug);
      if (categoryId) {
        this.filtros.categoria_id = categoryId;
      }
    } else if (params['id']) {
      this.filtros.categoria_id = +params['id'];
    } else {
      this.filtros.categoria_id = null;
    }

    this.loadProductos();
    this.actualizarTitulo();
    this.updateCategoryContext();
  }

  private getCategoryIdFromSlug(slug: string): number | null {
    if (this.categorySlugMap[slug] !== undefined) {
      return this.categorySlugMap[slug];
    }
    const normalizedSlug = this.normalizeSlug(slug);
    if (this.categorySlugMap[normalizedSlug] !== undefined) {
      return this.categorySlugMap[normalizedSlug];
    }
    const lowerSlug = slug.toLowerCase();
    const keys = Object.keys(this.categorySlugMap);
    for (const key of keys) {
      if (key.toLowerCase() === lowerSlug) {
        return this.categorySlugMap[key];
      }
    }
    return null;
  }

  private normalizeSlug(text: string): string {
    return text.toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  actualizarTitulo() {
    const ofertas = this.route.snapshot.queryParams['ofertas'];
    if (ofertas === 'true') {
      this.tituloActual = 'OFERTAS';
      return;
    }

    const categoriaId = this.filtros.categoria_id;
    if (!categoriaId) {
      this.tituloActual = 'PRODUCTOS';
      return;
    }

    const categoria = this.findCategoryById(categoriaId);
    if (categoria) {
      const parts = [categoria.nombre.toUpperCase()];
      let parentId = categoria.categoria_padre_id;

      while (parentId) {
        const parent = this.findCategoryById(parentId);
        if (parent) {
          parts.unshift(parent.nombre.toUpperCase());
          parentId = parent.categoria_padre_id;
        } else {
          break;
        }
      }

      this.tituloActual = parts.join(' > ');
      return;
    }

    this.tituloActual = 'PRODUCTOS';
  }

  // ⚡ OPTIMIZACIÓN: Función principal de carga
  loadProductos() {
    console.log('🔄 Cargando productos...');
    this.showNoProducts = false;
    this.loading = true;
    this.currentPage = 1;

    const filtrosEnviar: any = {};
    if (this.busqueda) filtrosEnviar.busqueda = this.busqueda;
    if (this.filtros.categoria_id) filtrosEnviar.categoria_id = this.filtros.categoria_id;
    if (this.filtros.destacados) filtrosEnviar.destacados = true;
    if (this.filtros.color) filtrosEnviar.color = this.filtros.color;
    if (this.filtros.talle_id) filtrosEnviar.talle_id = this.filtros.talle_id;
    if (this.filtros.dorsal) filtrosEnviar.dorsal = this.filtros.dorsal;
    if (this.filtros.numero !== null) filtrosEnviar.numero = this.filtros.numero;
    if (this.filtros.version) filtrosEnviar.version = this.filtros.version;
    if (this.filtros.precio_min !== null) filtrosEnviar.precio_min = this.filtros.precio_min;
    if (this.filtros.precio_max !== null) filtrosEnviar.precio_max = this.filtros.precio_max;
    if (this.filtros.ordenar_por) filtrosEnviar.ordenar_por = this.filtros.ordenar_por;

    const queryParams = this.route.snapshot.queryParams;
    if (queryParams['ofertas'] === 'true') {
      filtrosEnviar.ofertas = true;
    }

    filtrosEnviar.page = 1;
    filtrosEnviar.page_size = this.pageSize;

    // ⚡ Si es carga básica (sin filtros), usar caché precargada
    const isBasicLoad = !this.busqueda && !this.filtros.categoria_id && 
                        !this.filtros.color && !this.filtros.talle_id && 
                        this.filtros.ordenar_por === 'destacado';

    if (isBasicLoad && this.currentPage === 1) {
      this.productoService.cargarProductos().pipe(
        tap((productos) => {
          this.productos = productos.slice(0, this.pageSize);
          this.totalProducts = productos.length;
          this.hasMoreProducts = this.productos.length < this.totalProducts;
          this.ordenarProductosAgotadosAlFinal();
          this.extraerOpcionesFiltros();
        }),
        catchError((err) => {
          console.error('Error en precarga:', err);
          return of([]);
        }),
        takeUntil(this.destroy$)
      ).subscribe({
        next: () => {
          this.loading = false;
          
          // ⚡ DELAY de 3 segundos para el mensaje de "No disponible"
          if (this.productos.length === 0) {
            setTimeout(() => {
              this.showNoProducts = true;
              this.cdr.markForCheck();
            }, 3000);
          } else {
            this.showNoProducts = false;
          }
          
          this.cdr.markForCheck(); // ⚡ Actualizar vista
        },
        complete: () => {
          this.loading = false;
          this.cdr.markForCheck();
        }
      });
      return;
    }

    // Si hay filtros, usar API normal
    this.apiService.getProductos(filtrosEnviar).pipe(
      tap((data) => {
        this.productos = data.items || data;
        this.totalProducts = data.total || this.productos.length;
        this.hasMoreProducts = this.productos.length < this.totalProducts;
        this.ordenarProductosAgotadosAlFinal();
        this.extraerOpcionesFiltros();
      }),
      catchError((error) => {
        console.error('Error cargando productos:', error);
        return of({ items: [], total: 0 });
      }),
      takeUntil(this.destroy$)
    ).subscribe({
      next: () => {
        this.loading = false;

        // ⚡ DELAY de 3 segundos para el mensaje de "No disponible"
        if (this.productos.length === 0) {
          setTimeout(() => {
            this.showNoProducts = true;
            this.cdr.markForCheck();
          }, 3000);
        } else {
          this.showNoProducts = false;
        }

        this.cdr.markForCheck();
      },
      complete: () => {
        this.loading = false;
        this.cdr.markForCheck(); // ⚡ Actualizar vista
      }
    });
  }

  loadMoreProductos() {
    if (this.loadingMore || !this.hasMoreProducts) return;

    this.loadingMore = true;
    this.currentPage++;

    const filtrosEnviar: any = {
      page: this.currentPage,
      page_size: this.pageSize
    };

    if (this.busqueda) filtrosEnviar.busqueda = this.busqueda;
    if (this.filtros.categoria_id) filtrosEnviar.categoria_id = this.filtros.categoria_id;
    if (this.filtros.destacados) filtrosEnviar.destacados = true;
    if (this.filtros.color) filtrosEnviar.color = this.filtros.color;
    if (this.filtros.talle_id) filtrosEnviar.talle_id = this.filtros.talle_id;
    if (this.filtros.dorsal) filtrosEnviar.dorsal = this.filtros.dorsal;
    if (this.filtros.numero !== null) filtrosEnviar.numero = this.filtros.numero;
    if (this.filtros.version) filtrosEnviar.version = this.filtros.version;
    if (this.filtros.precio_min !== null) filtrosEnviar.precio_min = this.filtros.precio_min;
    if (this.filtros.precio_max !== null) filtrosEnviar.precio_max = this.filtros.precio_max;

    this.apiService.getProductos(filtrosEnviar).pipe(
      tap((data) => {
        const newProducts = data.items || data;
        this.productos = [...this.productos, ...newProducts];
        this.totalProducts = data.total || this.productos.length;
        this.hasMoreProducts = this.productos.length < this.totalProducts;
        this.ordenarProductosAgotadosAlFinal();
        this.extraerOpcionesFiltros();
      }),
      takeUntil(this.destroy$)
    ).subscribe({
      next: () => {
        this.loadingMore = false;
        this.cdr.markForCheck();
      },
      complete: () => {
        this.loadingMore = false;
        this.cdr.markForCheck();
      }
    });
  }

  extraerOpcionesFiltros() {
    const colores = new Set<string>();
    const dorsales = new Set<string>();
    const numeros = new Set<number>();

    this.productos.forEach(p => {
      if (p.color) colores.add(p.color);
      if (p.dorsal) dorsales.add(p.dorsal);
      if (p.numero !== null) numeros.add(p.numero);
    });

    this.coloresDisponibles = Array.from(colores).sort();
    this.dorsalesDisponibles = Array.from(dorsales).sort();
    this.numerosDisponibles = Array.from(numeros).sort((a, b) => a - b);
  }

  loadCategorias(): Observable<void> {
    return this.apiService.getCategorias(true, undefined, true).pipe(
      map((data: any[]) => {
        const categoryMap = new Map();
        data.forEach((cat: any) => {
          cat.subcategorias = [];
          categoryMap.set(cat.id, cat);
          
          const slug = cat.slug ? cat.slug : this.normalizeSlug(cat.nombre);
          this.categorySlugMap[slug] = cat.id;
          this.categoryIdToSlug[cat.id] = slug;
        });

        const roots: any[] = [];
        data.forEach((cat: any) => {
          if (cat.categoria_padre_id) {
            const parent = categoryMap.get(cat.categoria_padre_id);
            if (parent) {
              // Evitar duplicados: check if ID already exists in subcategorias
              const exists = parent.subcategorias.some((s: any) => s.id === cat.id);
              if (!exists) {
                parent.subcategorias.push(cat);
              }
            }
          } else {
            // Evitar duplicados en roots
            const exists = roots.some((r: any) => r.id === cat.id);
            if (!exists) {
              roots.push(cat);
            }
          }
        });

        data.forEach(cat => {
          if (cat.subcategorias) {
            cat.subcategorias.sort((a: any, b: any) => a.nombre.localeCompare(b.nombre));
          }
        });

        this.categorias = roots.sort((a, b) => a.nombre.localeCompare(b.nombre));
        this.buildCategoriesMap(this.categorias);
        this.actualizarTitulo();
        this.updateCategoryContext();
        this.cdr.markForCheck();
      }),
      catchError((error) => {
        console.error('Error categorías:', error);
        return of(void 0);
      })
    );
  }

  loadTalles(): Observable<void> {
    return this.apiService.getTalles().pipe(
      tap((data) => {
        this.talles = data;
        console.log('✅ Talles cargados:', data.length);
        this.cdr.markForCheck();
      }),
      map(() => void 0),  // ⚡ Retorna void, no los datos
      catchError((error) => {
        console.error('❌ Error talles:', error);
        return of(void 0);
      })
    );
  }

  filtrarPorCategoria(categoriaId: number | null) {
    this.filtros.categoria_id = categoriaId;
    if (categoriaId) {
      this.router.navigate(['/categoria', categoriaId]);
    } else {
      this.router.navigate(['/productos']);
    }
    this.loadProductos();
  }

  aplicarFiltros() {
    this.filtros.precio_min = this.precioMinInput ? parseFloat(this.precioMinInput) : null;
    this.filtros.precio_max = this.precioMaxInput ? parseFloat(this.precioMaxInput) : null;
    this.loadProductos();
  }

  limpiarFiltros() {
    this.filtros = {
      categoria_id: null,
      destacados: false,
      color: '',
      talle_id: null,
      dorsal: '',
      numero: null,
      version: '',
      precio_min: null,
      precio_max: null,
      ordenar_por: 'destacado'
    };
    this.precioMinInput = '';
    this.precioMaxInput = '';
    this.busqueda = '';
    this.loadProductos();
  }

  cambiarOrdenamiento(orden: string) {
    this.filtros.ordenar_por = orden;
    this.loadProductos();
  }

  buscar() {
    this.loadProductos();
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

  getPrecioTransferencia(producto: any): number {
    let esShort = false;
    if (producto.categoria_id === 8) {
      esShort = true;
    } else {
      let cat = this.findCategoryById(producto.categoria_id);
      let attempts = 0;
      while (cat && attempts < 5) {
        if (cat.id === 8 || cat.id === 2 || (cat.nombre && cat.nombre.toLowerCase().trim() === 'shorts')) {
          esShort = true;
          break;
        }
        if (cat.categoria_padre_id) {
          cat = this.findCategoryById(cat.categoria_padre_id);
        } else {
          break;
        }
        attempts++;
      }
    }

    const porcentaje = esShort ? 0.90 : 0.85;
    return this.getPrecioFinal(producto) * porcentaje;
  }

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

  getDescuentoPorcentaje(producto: any): number {
    const precioBase = producto.precio_base;
    const precioFinal = this.getPrecioFinal(producto);

    if (!precioBase || precioFinal >= precioBase) return 0;
    return Math.round((1 - (precioFinal / precioBase)) * 100);
  }

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

  getCuotaSinInteres(producto: any): number {
    return this.getPrecioFinal(producto) / 3;
  }

  updateCategoryContext() {
    const categoriaId = this.filtros.categoria_id;

    if (!categoriaId) {
      this.currentCategoryLevel = 0;
      this.currentCategory = null;
      this.parentCategory = null;
      return;
    }

    const cat = this.findCategoryById(categoriaId);

    if (cat) {
      this.currentCategory = cat;
      let level = 1;
      let parentId = cat.categoria_padre_id;
      let parent = null;

      while (parentId) {
        level++;
        const p = this.findCategoryById(parentId);
        if (p) {
          if (level === 2) this.parentCategory = p;
          parentId = p.categoria_padre_id;
        } else {
          break;
        }
      }
      this.currentCategoryLevel = level;

      if (cat.categoria_padre_id) {
        this.parentCategory = this.findCategoryById(cat.categoria_padre_id);
      } else {
        this.parentCategory = null;
      }
    }
  }

  getSidebarCategories(): any[] {
    if (this.currentCategoryLevel === 0) {
      return this.categorias;
    }

    if (this.currentCategory) {
      // Si la categoría actual tiene subcategorías, mostrarlas para seguir bajando
      if (this.currentCategory.subcategorias && this.currentCategory.subcategorias.length > 0) {
        return this.currentCategory.subcategorias;
      }

      // Si no tiene subcategorías, mostrar sus hermanas (hijas del padre)
      if (this.parentCategory && this.parentCategory.subcategorias) {
        return this.parentCategory.subcategorias;
      }
    }

    return this.categorias;
  }

  getSidebarTitle(): string {
    if (this.currentCategoryLevel === 0) {
      return 'CATEGORÍAS';
    }
    if (this.currentCategory) {
      if (this.currentCategory.subcategorias && this.currentCategory.subcategorias.length > 0) {
        return this.currentCategory.nombre.toUpperCase();
      }
      if (this.parentCategory) {
        return this.parentCategory.nombre.toUpperCase();
      }

      return this.currentCategory.nombre.toUpperCase();
    }
    return 'CATEGORÍAS';
  }

  getCategoryPath(category: any): any[] {
    const slug = this.categoryIdToSlug[category.id];
    if (!slug) return ['/productos'];

    const pathParts = [slug];
    let parentId = category.categoria_padre_id;

    while (parentId) {
      const parent = this.findCategoryById(parentId);
      if (parent) {
        const parentSlug = this.categoryIdToSlug[parent.id];
        if (parentSlug) {
          pathParts.unshift(parentSlug);
        }
        parentId = parent.categoria_padre_id;
      } else {
        break;
      }
    }

    return ['/categoria', ...pathParts];
  }

  buildCategoriesMap(nodes: any[]) {
    nodes.forEach(node => {
      this.categoriesMap.set(node.id, node);
      if (node.subcategorias && node.subcategorias.length > 0) {
        this.buildCategoriesMap(node.subcategorias);
      }
    });
  }

  findCategoryById(id: number): any {
    return this.categoriesMap.get(id);
  }

  navigateToCategory(categoriaId: number) {
    const category = this.findCategoryById(categoriaId);
    if (category) {
      const path = this.getCategoryPath(category);
      this.router.navigate(path).then(() => {
        this.updateCategoryContext();
      });
    } else {
      this.router.navigate(['/categoria', categoriaId]);
    }
  }

  navigateBack() {
    if (this.parentCategory) {
      this.navigateToCategory(this.parentCategory.id);
    } else {
      this.router.navigate(['/productos']);
    }
  }

  private ordenarProductosAgotadosAlFinal() {
    this.productos.sort((a, b) => {
      if (!!a.esta_agotado === !!b.esta_agotado) return 0;
      return a.esta_agotado ? 1 : -1;
    });
  }
}
