import { Component, EventEmitter, Output, ChangeDetectorRef, NgZone, Input, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject, of, forkJoin } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap } from 'rxjs/operators';
import { ApiService } from '../../../services/api.service';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-add-stock-form',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="add-stock-form">
      <!-- PRODUCT SEARCH -->
      <div class="product-search-container">
        <label style="font-weight: 700; color: #1e293b; margin-bottom: 8px; display: block;">Buscar y Añadir Productos</label>
        <div style="position: relative;">
          <input
            type="text"
            class="form-control"
            [(ngModel)]="searchQuery"
            (input)="onSearchInput($event)"
            placeholder="Ej: Liverpool, Suplente, Messi..."
            autocomplete="off"
            style="padding-right: 40px;"
          />
          <i class="fas fa-search" style="position: absolute; right: 15px; top: 12px; color: #94a3b8;"></i>
        </div>
        
        <!-- SEARCH RESULTS DROPDOWN (Aesthetic) -->
        <div class="search-results" *ngIf="searchResults.length > 0">
          <div
            class="search-result-item"
            *ngFor="let product of searchResults"
            (click)="selectProduct(product)"
          >
            <img [src]="getImagenPrincipal(product)" alt="product">
            <div class="result-info">
              <div class="result-name">{{ product.nombre }}</div>
              <div class="result-meta">
                <span>{{ product.version || 'Original' }}</span>
                <span *ngIf="product.color" style="opacity: 0.5;"> • </span>
                <span>{{ product.color }}</span>
              </div>
            </div>
            <div class="result-icon">
              <i class="fas fa-plus-circle"></i>
            </div>
          </div>
        </div>
        
        <!-- SEARCHING INDICATOR -->
        <div class="search-results" *ngIf="searching">
          <div class="search-result-item" style="justify-content: center; color: #64748b;">
            <i class="fas fa-spinner fa-spin"></i>
            <span style="margin-left: 10px;">Buscando productos...</span>
          </div>
        </div>
      </div>

      <!-- SELECTED PRODUCTS CHIPS (Multi-selection) -->
      <div class="selected-products-container" *ngIf="selectedProducts.length > 0">
        <div class="product-chip" *ngFor="let prod of selectedProducts; let i = index">
          <img [src]="getImagenPrincipal(prod)" alt="thumb">
          <div class="chip-name">{{ prod.nombre }}</div>
          <button type="button" class="btn-remove-chip" (click)="removeProduct(i)">
            <i class="fas fa-times-circle"></i>
          </button>
        </div>
      </div>

      <div class="alert alert-info" *ngIf="selectedProducts.length === 0" style="padding: 1rem; border-radius: 8px; background: #eff6ff; color: #1e40af; font-size: 0.9rem; margin-bottom: 1.5rem; display: flex; align-items: center; gap: 10px;">
        <i class="fas fa-info-circle"></i>
        <span>Busca y selecciona uno o más productos para agregarles stock masivamente.</span>
      </div>

      <!-- SIZE INPUTS (S, M, L, XL, XXL) -->
      <div *ngIf="selectedProducts.length > 0">
        <label style="display: block; margin-bottom: 1rem; font-weight: 700; color: #1e293b; font-size: 1rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 5px;">
           Stock a SUMAR (para los {{ selectedProducts.length }} productos)
        </label>
        <div class="sizes-grid" style="background: #f8fafc; padding: 1.5rem; border-radius: 12px; border: 1px solid #e2e8f0;">
          <div class="size-input-group" *ngFor="let size of sizes">
            <label>{{ size }}</label>
            <input
              type="number"
              [(ngModel)]="sizeInputs[size]"
              min="0"
              placeholder="0"
              style="font-weight: 700; color: #0f172a;"
            />
          </div>
        </div>
        <small style="color: #64748b; margin-top: 10px; display: block;">* Las cantidades ingresadas se sumarán al stock actual de cada producto seleccionado.</small>
      </div>

      <!-- FORM ACTIONS -->
      <div class="form-actions" style="margin-top: 2rem;">
        <button
          type="button"
          class="btn btn-success"
          (click)="submitStock()"
          [disabled]="selectedProducts.length === 0 || submitting"
          style="background: #10b981; border: none; font-weight: 700; height: 50px; display: flex; align-items: center; justify-content: center; gap: 10px;"
        >
          <i class="fas" [class.fa-save]="!submitting" [class.fa-spinner]="submitting" [class.fa-spin]="submitting"></i>
          {{ submitting ? 'Guardando cambios...' : '🚀 Guardar Todo el Stock' }}
        </button>
        <button
          type="button"
          class="btn btn-secondary"
          (click)="cancel()"
          [disabled]="submitting"
          style="background: #94a3b8; border: none; font-weight: 600; height: 50px;"
        >
          Cancelar
        </button>
      </div>
    </div>
  `
})
export class AddStockFormComponent implements OnInit, OnChanges {
  @Input() preSelectedProductId: number | null = null;
  @Output() stockAdded = new EventEmitter<void>();
  @Output() cancelled = new EventEmitter<void>();

  selectedProducts: any[] = [];
  searchQuery = '';
  searchResults: any[] = [];
  searching = false;
  submitting = false;

  sizes = ['S', 'M', 'L', 'XL', 'XXL'];
  sizeInputs: { [key: string]: number } = {
    S: 0,
    M: 0,
    L: 0,
    XL: 0,
    XXL: 0
  };

  private searchSubject = new Subject<string>();

  ngOnInit() {
    if (this.preSelectedProductId) {
      this.loadAndSelectProduct(this.preSelectedProductId);
    }
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['preSelectedProductId'] && changes['preSelectedProductId'].currentValue) {
      this.loadAndSelectProduct(changes['preSelectedProductId'].currentValue);
    }
  }

  loadAndSelectProduct(id: number) {
    // Si ya está seleccionado, no lo cargues de nuevo
    if (this.selectedProducts.find(p => p.id === id)) return;

    this.apiService.getProducto(id).subscribe({
      next: (prod) => {
        this.selectProduct(prod);
      },
      error: (err) => {
        console.error('Error fetching product by ID:', err);
      }
    });
  }

  constructor(
    private apiService: ApiService,
    private cdr: ChangeDetectorRef,
    private zone: NgZone
  ) {
    // Setup debounced search
    this.searchSubject.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      switchMap(query => {
        if (query.length < 2) {
          return of([]);
        }
        this.zone.run(() => {
          this.searching = true;
          this.cdr.detectChanges();
        });
        return this.apiService.searchProducts(query);
      })
    ).subscribe({
      next: (results: any) => {
        this.zone.run(() => {
          // Filtrar los que ya están seleccionados
          this.searchResults = results.filter((r: any) => !this.selectedProducts.find(p => p.id === r.id));
          this.searching = false;
          this.cdr.detectChanges();
        });
      },
      error: (error) => {
        console.error('Error searching products:', error);
        this.zone.run(() => {
          this.searching = false;
          this.searchResults = [];
          this.cdr.detectChanges();
        });
      }
    });
  }

  onSearchInput(event: Event) {
    const value = (event.target as HTMLInputElement).value;
    this.searchQuery = value;
    this.searchSubject.next(value);
  }

  selectProduct(product: any) {
    // Evitar duplicados
    if (this.selectedProducts.find(p => p.id === product.id)) {
        this.searchQuery = '';
        this.searchResults = [];
        return;
    }

    this.selectedProducts.push(product);
    this.searchQuery = '';
    this.searchResults = [];
    
    // Forzar actualización de UI
    this.cdr.detectChanges();
  }

  removeProduct(index: number) {
    this.selectedProducts.splice(index, 1);
    this.cdr.detectChanges();
  }

  getImagenPrincipal(product: any): string {
    if (product.imagenes && product.imagenes.length > 0) {
      const principal = product.imagenes.find((img: any) => img.es_principal);
      return principal ? principal.url : product.imagenes[0].url;
    }
    return '/assets/no-image.png';
  }

  clearSelection() {
    this.selectedProducts = [];
    this.searchQuery = '';
    this.searchResults = [];
  }

  submitStock() {
    if (this.selectedProducts.length === 0) {
      Swal.fire('Atención', 'Selecciona al menos un producto', 'warning');
      return;
    }

    // Filter out zero values
    const increments: any = {};
    this.sizes.forEach(size => {
      if (this.sizeInputs[size] > 0) {
        increments[size] = this.sizeInputs[size];
      }
    });

    if (Object.keys(increments).length === 0) {
      Swal.fire('Atención', 'Ingresa al menos una cantidad para sumar', 'warning');
      return;
    }

    this.submitting = true;

    // Ejecutar todas las actualizaciones en paralelo
    const requests = this.selectedProducts.map(prod => 
      this.apiService.addStockBySizes(prod.id, increments)
    );

    forkJoin(requests).subscribe({
      next: (responses) => {
        Swal.fire({
          icon: 'success',
          title: 'Stock Actualizado',
          text: `Se actualizó el stock correctamente para ${this.selectedProducts.length} productos.`,
          timer: 2500,
          showConfirmButton: false,
          confirmButtonColor: '#000'
        });
        this.stockAdded.emit();
      },
      error: (error) => {
        console.error('Error adding bulk stock:', error);
        Swal.fire('Error', 'Hubo un problema al actualizar el stock de algunos productos.', 'error');
        this.submitting = false;
      }
    });
  }

  cancel() {
    this.cancelled.emit();
  }
}
