import { Component, OnInit, HostListener, ElementRef, ChangeDetectorRef } from '@angular/core';
import { Observable, Subject, of } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, catchError, tap } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { CartService } from '../../services/cart.service';
import { AuthService } from '../../services/auth.service';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './header.html',
  styleUrl: './header.css'
})
export class HeaderComponent implements OnInit {
  categorias: any[] = [];
  categoriasTree: any[] = [];
  cartItemCount = 0;
  cartTotal$: Observable<number>; // Observable version
  isAdmin = false;
  isCliente = false;
  currentUser: any = null;
  menuOpen = false;
  isProductsMenuOpen = false;
  activeCategory: any | null = null;
  busqueda = '';

  // Carrito Offcanvas
  isCartOpen = false;
  cartItems$: Observable<any[]>;

  // Acordeón Móvil
  expandedCategories: { [key: number]: boolean } = {};

  // Autocomplete
  private searchTerms = new Subject<string>();
  searchResults: any[] = [];
  showSearchResults = false;
  isSearching = false;

  private menuCloseTimeout: any;

  constructor(
    private router: Router,
    public cartService: CartService, // Make public for template access if needed, or use property
    private authService: AuthService,
    public apiService: ApiService, // Public for template usage of helper methods
    private el: ElementRef,
    private cdr: ChangeDetectorRef
  ) {
    this.cartTotal$ = this.cartService.total$;
    this.cartItems$ = this.cartService.cart$;
  }

  ngOnInit() {
    this.loadCategorias();
    this.updateAuthState();

    this.cartService.cart$.subscribe(items => {
      this.cartItemCount = items.reduce((sum, item) => sum + (item.cantidad || 0), 0);
      // We don't need to manually set cartTotal anymore, AsyncPipe handles total$
    });

    // Suscribirse para cambios futuros
    this.authService.isAuthenticated$.subscribe(() => {
      this.updateAuthState();
    });

    // Configurar búsqueda predictiva
    this.searchTerms.pipe(
      debounceTime(200), // Más rápido (200ms)
      distinctUntilChanged(),
      tap(() => {
        this.isSearching = true;
        this.showSearchResults = true;
        this.cdr.markForCheck(); // Forzar actualización UI estado loading
      }),
      switchMap((term: string) => {
        if (!term.trim()) {
          return of({ items: [] });
        }
        return this.apiService.getProductos({ busqueda: term, page_size: 6 }).pipe(
          catchError(error => {
            console.error('Error en búsqueda predictiva:', error);
            return of({ items: [] });
          })
        );
      })
    ).subscribe((data: any) => {
      this.isSearching = false;
      this.searchResults = data.items || [];
      this.cdr.detectChanges(); // Forzar actualización final
    });
  }

  updateAuthState() {
    this.isAdmin = !!this.authService.getAdmin();
    this.isCliente = !!this.authService.getCliente();
    this.currentUser = this.isAdmin ? this.authService.getAdmin() : this.authService.getCliente();
  }

  loadCategorias() {
    // Cargar lista plana para otros usos
    this.apiService.getCategorias().subscribe({
      next: (data) => {
        this.categorias = data;
      },
      error: (error) => {
        console.error('Error cargando categorías:', error);
      }
    });

    // Cargar árbol para el mega-menú
    this.apiService.getCategoriasTree().subscribe({
      next: (data) => {
        this.categoriasTree = data;
        console.log('🌳 Árbol de categorías cargado:', this.categoriasTree);
      },
      error: (error) => {
        console.error('Error cargando árbol de categorías:', error);
      }
    });
  }

  // Abrir el menú de productos
  openProductsMenu() {
    this.cancelCloseProductsMenu();
    this.isProductsMenuOpen = true;
  }

  // Programar cierre del menú con delay
  scheduleCloseProductsMenu() {
    this.menuCloseTimeout = setTimeout(() => {
      this.isProductsMenuOpen = false;
      this.clearActiveCategory();
    }, 150); // 150ms de delay para evitar parpadeos, cerrar más rápido
  }

  // Cancelar cierre pendiente
  cancelCloseProductsMenu() {
    if (this.menuCloseTimeout) {
      clearTimeout(this.menuCloseTimeout);
      this.menuCloseTimeout = null;
    }
  }

  // Cerrar menú inmediatamente (al hacer click o salir del mega-menu)
  closeProductsMenuNow() {
    this.cancelCloseProductsMenu();
    this.isProductsMenuOpen = false;
    this.clearActiveCategory();
  }

  // Establecer categoría activa y mostrar sus subcategorías
  setActiveCategory(category: any) {
    this.activeCategory = category;
  }

  // Limpiar categoría activa (ocultar subcategorías)
  clearActiveCategory() {
    this.activeCategory = null;
  }

  toggleMenu() {
    this.menuOpen = !this.menuOpen;
  }

  goToCart() {
    this.isCartOpen = true;
  }

  closeCart() {
    this.isCartOpen = false;
  }

  toggleSubcategory(event: Event, catId: number) {
    event.preventDefault();
    event.stopPropagation();
    this.expandedCategories[catId] = !this.expandedCategories[catId];
  }

  goToFullCart() {
    this.isCartOpen = false;
    this.router.navigate(['/carrito']);
  }

  goToAdmin() {
    if (this.isAdmin) {
      this.router.navigate(['/admin']);
    } else {
      this.router.navigate(['/admin/login']);
    }
  }

  logout() {
    this.authService.logout();
  }

  // Búsqueda
  onSearchInput(term: string): void {
    this.busqueda = term;
    this.searchTerms.next(term);
  }

  buscarProductos() {
    if (this.busqueda.trim()) {
      this.showSearchResults = false; // Ocultar dropdown al buscar
      this.router.navigate(['/productos'], { queryParams: { busqueda: this.busqueda.trim() } });
    }
  }

  selectSearchResult(producto: any) {
    this.busqueda = ''; // Limpiar búsqueda o mantenerla, según preferencia. Usualmente limpiar al ir al detalle.
    this.showSearchResults = false;
    this.router.navigate(['/productos', producto.id]);
  }

  onSearchBlur() {
    // Retrasar el cierre para permitir el click en el resultado
    setTimeout(() => {
      this.showSearchResults = false;
    }, 200);
  }

  onSearchFocus() {
    if (this.busqueda.trim()) {
      this.showSearchResults = true;
    }
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    // Cerrar menú de productos si click fuera
    if (!this.el.nativeElement.contains(event.target)) {
      this.isProductsMenuOpen = false;
      this.clearActiveCategory();
      this.showSearchResults = false;
    }
  }

  removeItem(index: number) {
    this.cartService.removeItem(index);
  }
}
