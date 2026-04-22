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
      <!-- STEP 1: SELECCIÓN -->
      <div *ngIf="currentStep === 1" class="step-container animated fadeIn">
        <div class="product-search-container cuadrado-box">
          <label style="font-weight: 700; color: #1e293b; margin-bottom: 12px; display: block; font-size: 1.1rem;">
            <i class="fas fa-search"></i> PASO 1: Seleccionar Productos
          </label>
          <div style="position: relative;">
            <input
              type="text"
              class="form-control"
              [(ngModel)]="searchQuery"
              (input)="onSearchInput($event)"
              placeholder="Buscar por nombre, talle o color..."
              autocomplete="off"
              style="padding: 12px 40px 12px 15px; border-radius: 10px;"
            />
            <i class="fas fa-search" style="position: absolute; right: 15px; top: 15px; color: #94a3b8;"></i>
            
            <!-- SEARCH RESULTS DROPDOWN -->
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
                    <span class="version-badge" *ngIf="product.version">{{ product.version }}</span>
                    <span *ngIf="product.color" style="margin-left: 8px;">• {{ product.color }}</span>
                  </div>
                </div>
                <button class="btn-add-search"><i class="fas fa-plus"></i> Añadir</button>
              </div>
            </div>
          </div>
        </div>

        <!-- SELECTED PRODUCTS AREA -->
        <div class="selected-area cuadrado-box" style="margin-top: 20px;" *ngIf="selectedProducts.length > 0">
          <label style="font-weight: 700; color: #1e293b; margin-bottom: 12px; display: block;">Productos Seleccionados ({{ selectedProducts.length }})</label>
          <div class="selected-products-container">
            <div class="product-chip" *ngFor="let prod of selectedProducts; let i = index">
              <img [src]="getImagenPrincipal(prod)" alt="thumb">
              <div class="chip-name">{{ prod.nombre }}</div>
              <button type="button" class="btn-remove-chip" (click)="removeProduct(i)">
                <i class="fas fa-times-circle"></i>
              </button>
            </div>
          </div>
          
          <button type="button" class="btn-primary" (click)="nextStep()" style="width: 100%; margin-top: 20px; height: 50px; font-weight: 700; font-size: 1rem; border-radius: 10px;">
            CONTINUAR A CARGA DE STOCK <i class="fas fa-arrow-right"></i>
          </button>
        </div>

        <div class="alert alert-info" *ngIf="selectedProducts.length === 0" style="margin-top: 20px; border-radius: 12px;">
          <i class="fas fa-info-circle"></i> Busca un producto para comenzar.
        </div>
      </div>

      <!-- STEP 2: CARGA DE STOCK -->
      <div *ngIf="currentStep === 2" class="step-container animated fadeIn">
        <div class="cuadrado-box" style="border-left: 5px solid #10b981;">
           <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
              <div>
                <label style="font-weight: 700; color: #1e293b; display: block; font-size: 1.1rem;">
                  <i class="fas fa-boxes"></i> PASO 2: Cargar Cantidades
                </label>
                <small style="color: #64748b;">Incrementando stock para {{ selectedProducts.length }} productos seleccionados.</small>
              </div>
              <button type="button" class="btn-link" (click)="prevStep()" style="color: #2563eb; font-weight: 600; text-decoration: none;">
                <i class="fas fa-edit"></i> Editar lista
              </button>
           </div>
           
           <div class="sizes-grid" style="background: #f8fafc; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px;">
            <div class="size-input-group" *ngFor="let size of sizes">
              <label>{{ size }}</label>
              <input
                type="number"
                [(ngModel)]="sizeInputs[size]"
                min="0"
                placeholder="0"
                style="font-weight: 700; text-align: center; font-size: 1.2rem; border-color: #cbd5e1;"
              />
            </div>
          </div>

          <div style="display: flex; gap: 10px;">
            <button
              type="button"
              class="btn btn-success"
              (click)="submitStock()"
              [disabled]="submitting"
              style="flex: 2; height: 55px; font-weight: 800; font-size: 1.1rem; border-radius: 10px; background: #10b981; border: none; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);"
            >
              <i class="fas" [class.fa-check-circle]="!submitting" [class.fa-spinner]="submitting" [class.fa-spin]="submitting"></i>
              {{ submitting ? 'GUARDANDO...' : 'CONFIRMAR Y GUARDAR STOCK' }}
            </button>
            <button
              type="button"
              class="btn btn-secondary"
              (click)="prevStep()"
              [disabled]="submitting"
              style="flex: 1; height: 55px; border-radius: 10px; background: #94a3b8; border: none;"
            >
              VOLVER
            </button>
          </div>
        </div>
      </div>

      <!-- FOOTER ACTIONS -->
      <div class="form-actions" style="margin-top: 2rem;" *ngIf="currentStep === 1">
        <button type="button" class="btn btn-secondary" (click)="cancel()" style="width: 100%; background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; font-weight: 600; height: 45px;">
          CANCELAR OPERACIÓN
        </button>
      </div>
    </div>
  `
})
export class AddStockFormComponent implements OnInit, OnChanges {
  @Input() preSelectedProductId: number | null = null;
  @Output() stockAdded = new EventEmitter<void>();
  @Output() cancelled = new EventEmitter<void>();

  currentStep: number = 1; // 1: Selección, 2: Carga de Stock
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
    this.searchSubject.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      switchMap(query => {
        if (query.length < 2) return of([]);
        this.zone.run(() => {
          this.searching = true;
          this.cdr.detectChanges();
        });
        return this.apiService.searchProducts(query);
      })
    ).subscribe({
      next: (results: any) => {
        this.zone.run(() => {
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
    if (this.selectedProducts.find(p => p.id === product.id)) {
        this.searchQuery = '';
        this.searchResults = [];
        return;
    }
    this.selectedProducts.push(product);
    this.searchQuery = '';
    this.searchResults = [];
    this.cdr.detectChanges();
  }

  removeProduct(index: number) {
    this.selectedProducts.splice(index, 1);
    if (this.selectedProducts.length === 0) this.currentStep = 1;
    this.cdr.detectChanges();
  }

  getImagenPrincipal(product: any): string {
    if (product.imagen_principal) return product.imagen_principal;
    if (product.imagenes && product.imagenes.length > 0) {
      const principal = product.imagenes.find((img: any) => img.es_principal);
      return principal ? principal.url : product.imagenes[0].url;
    }
    return '/assets/logo.png';
  }

  clearSelection() {
    this.selectedProducts = [];
    this.currentStep = 1;
    this.searchQuery = '';
    this.searchResults = [];
  }

  nextStep() {
    if (this.selectedProducts.length > 0) {
      this.currentStep = 2;
      this.cdr.detectChanges();
    }
  }

  prevStep() {
    this.currentStep = 1;
    this.cdr.detectChanges();
  }

  submitStock() {
    if (this.selectedProducts.length === 0) {
      Swal.fire('Atención', 'Selecciona al menos un producto', 'warning');
      return;
    }
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
          showConfirmButton: false
        });
        this.stockAdded.emit();
      },
      error: (error) => {
        console.error('Error adding bulk stock:', error);
        Swal.fire('Error', 'Hubo un problema al actualizar el stock.', 'error');
        this.submitting = false;
      }
    });
  }

  cancel() {
    this.cancelled.emit();
  }
}
