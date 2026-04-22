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
        <div class="product-search-container cuadrado-box" style="padding-bottom: 5px;">
          <label style="font-weight: 800; color: #0f172a; margin-bottom: 15px; display: block; font-size: 1.2rem; letter-spacing: -0.5px;">
            <i class="fas fa-search" style="color: #6366f1;"></i> 1. Buscar Camisetas
          </label>
          <div style="position: relative;">
            <input
              type="text"
              class="form-control main-search-input"
              [(ngModel)]="searchQuery"
              (input)="onSearchInput($event)"
              placeholder="Ej: Argentina Titular, Messi, Liverpool..."
              autocomplete="off"
            />
            <i class="fas fa-search" style="position: absolute; right: 20px; top: 18px; color: #94a3b8; font-size: 1.2rem;"></i>
            
           <!-- SEARCH RESULTS DROPDOWN (Aesthetic List) -->
          <div class="search-results shadow-xl" *ngIf="searchResults.length > 0">
            <div
              class="search-result-item-row"
              *ngFor="let product of searchResults"
            >
              <div class="row-left">
                <div class="row-info">
                  <div class="row-name">{{ product.nombre }}</div>
                  <div class="row-meta">
                    <span class="version-label" [class.jugador]="product.version?.toLowerCase().includes('jugador')">
                      {{ product.version || 'Version no definida' }}
                    </span>
                    <span class="row-color" *ngIf="product.color">
                      • {{ product.color }}
                    </span>
                  </div>
                </div>
              </div>
              <button class="btn-click-add" (click)="selectProduct(product)">
                  <i class="fas fa-plus"></i> AÑADIR
              </button>
            </div>
          </div>
        </div>

        <!-- SELECTED PRODUCTS AREA (Vertical List Rows) -->
        <div class="selected-area" style="margin-top: 25px;" *ngIf="selectedProducts.length > 0">
          <label style="font-weight: 800; color: #0f172a; margin-bottom: 15px; display: block; font-size: 1.1rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">
             PRODUCTOS A ACTUALIZAR ({{ selectedProducts.length }})
          </label>
          
          <div class="selected-list-container">
            <div class="selected-row-card" *ngFor="let prod of selectedProducts; let i = index">
              <div class="card-info">
                <div class="card-name">{{ prod.nombre }}</div>
                <div class="card-meta">
                  <span style="font-weight: 700; color: #4338ca;">{{ prod.version }}</span> 
                  <span *ngIf="prod.color"> • {{ prod.color }}</span>
                </div>
              </div>
              <button type="button" class="btn-click-remove" (click)="removeProduct(i)" title="Eliminar de la lista">
                <i class="fas fa-trash-alt"></i> QUITAR
              </button>
            </div>
          </div>
          
          <button type="button" class="btn-continue-wizard shadow-lg" (click)="nextStep()">
            <span>SIGUIENTE: CARGAR STOCK</span>
            <i class="fas fa-chevron-right"></i>
          </button>
        </div>

        <div class="empty-state-placeholder animated pulse" *ngIf="selectedProducts.length === 0">
          <img src="/assets/logo.png" style="opacity: 0.1; width: 80px; margin-bottom: 15px;">
          <p>Busca y selecciona las camisetas que quieres actualizar.</p>
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
    const rawUrl = product.imagen_principal || (product.imagenes && product.imagenes.length > 0 ? (product.imagenes.find((img: any) => img.es_principal)?.url || product.imagenes[0].url) : null);
    return this.apiService.getFormattedImageUrl(rawUrl);
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
