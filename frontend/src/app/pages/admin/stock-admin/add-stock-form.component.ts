import { Component, EventEmitter, Output, ChangeDetectorRef, NgZone, Input, OnInit, OnChanges, SimpleChanges, ViewEncapsulation } from '@angular/core';
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
  styleUrl: './stock-administration.css',
  encapsulation: ViewEncapsulation.None,
    <div class="add-stock-form" style="min-height: 500px; background: white; display: block !important; width: 100%; position: relative; overflow: visible !important;">
      
      <!-- STEP 1: SELECCIÓN -->
      <div [style.display]="currentStep === 1 ? 'block' : 'none'" class="step-container" style="opacity: 1 !important; visibility: visible !important;">
        <div class="product-search-container cuadrado-box" style="padding-bottom: 5px; border-top: 4px solid #6366f1;">
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
              <div class="row-info">
                <div class="row-name">{{ product.nombre }}</div>
                <div class="row-meta">
                  <span class="version-label" [class.jugador]="product.version?.toLowerCase().includes('jugador')">
                    {{ product.version || 'No Definida' }}
                  </span>
                </div>
              </div>
              <button class="btn-click-add" (click)="selectProduct(product)">
                  <i class="fas fa-plus"></i> AÑADIR
              </button>
            </div>
          </div>
        </div>

        <!-- SELECTED PRODUCTS AREA -->
        <div class="selected-area" style="margin-top: 25px;" *ngIf="selectedProducts.length > 0">
          <label style="font-weight: 800; color: #0f172a; margin-bottom: 15px; display: block; font-size: 1.1rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">
             LISTA SELECCIONADA ({{ selectedProducts.length }})
          </label>
          
          <div class="selected-list-container">
            <div class="selected-row-card" *ngFor="let prod of selectedProducts; let i = index">
              <div class="card-info">
                <div class="card-name">{{ prod.nombre }}</div>
                <div class="card-meta">
                  <span class="version-badge-text" [class.jugador]="prod.version?.toLowerCase().includes('jugador')">
                    {{ prod.version || 'No Definida' }}
                  </span>
                </div>
              </div>
              <button type="button" class="btn-click-remove" (click)="removeProduct(i)">
                <i class="fas fa-trash-alt"></i> QUITAR
              </button>
            </div>
          </div>
          
          <button type="button" class="btn-continue-wizard shadow-lg" (click)="nextStep()">
            <span>CONTINUAR A CARGA DE STOCK</span>
            <i class="fas fa-chevron-right"></i>
          </button>
        </div>

        <div class="empty-state-placeholder" *ngIf="selectedProducts.length === 0" style="padding: 40px; text-align: center;">
          <p style="font-weight: 500; color: #64748b;">Busca y selecciona las camisetas que quieres actualizar.</p>
        </div>
      </div>

    <!-- STEP 2: CARGA DE STOCK (Absolute Visibility Mode) -->
    <div [style.display]="currentStep === 2 ? 'block' : 'none'" class="step-container" style="opacity: 1 !important; visibility: visible !important; background: #fffbeb !important; border: 3px dashed #f59e0b; padding: 10px; border-radius: 20px;">
      
      <div style="background: #10b981; color: white; padding: 10px; text-align: center; border-radius: 10px; margin-bottom: 15px; font-weight: 900;">
         CARGA DE STOCK ACTIVA - SI VES ESTO FUNCIONA
      </div>

      <div class="cuadrado-box" style="border-top: 5px solid #10b981; background-color: #ffffff; padding: 25px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.1);">
         <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 25px;">
            <div style="text-align: left;">
              <h2 style="font-weight: 800; color: #1e293b; margin: 0; font-size: 1.4rem;">
                PASO 2: Cargar Stock
              </h2>
              <p style="color: #64748b; font-weight: 600; margin: 5px 0;">Sumando stock a {{ selectedProducts.length }} productos.</p>
            </div>
            <button type="button" (click)="prevStep()" style="color: #4338ca; font-weight: 800; background: none; border: none; cursor: pointer; font-size: 0.95rem;">
              <i class="fas fa-arrow-left"></i> VOLVER ATRÁS
            </button>
         </div>
         
         <!-- GRID DE TALLES (Hardcoded) -->
         <div class="sizes-grid-container" style="display: grid !important; grid-template-columns: 1fr; gap: 12px; background: #f8fafc; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; overflow: visible !important;">
          
          <!-- ROW S -->
          <div class="size-row-item" style="display: flex !important; justify-content: space-between; align-items: center; background: white; padding: 10px 15px; border-radius: 10px; border: 1px solid #cbd5e1;">
            <div style="font-weight: 900; font-size: 1.1rem; color: #0f172a; width: 40px;">S</div>
            <div class="quantity-controller" style="display: flex; align-items: center; gap: 12px;">
              <button type="button" (click)="decrementStock('S')" style="width: 36px; height: 36px; border-radius: 50%; border: 2px solid #ef4444; background: white; color: #ef4444; font-size: 1.1rem; cursor: pointer; font-weight: 900;">-</button>
              <input type="number" [(ngModel)]="sizeInputs['S']" min="0" style="width: 60px; height: 40px; text-align: center; font-size: 1.3rem; font-weight: 900; border: none; background: #f1f5f9; border-radius: 8px; color: #1e293b;" />
              <button type="button" (click)="incrementStock('S')" style="width: 36px; height: 36px; border-radius: 50%; border: 2px solid #10b981; background: white; color: #10b981; font-size: 1.1rem; cursor: pointer; font-weight: 900;">+</button>
            </div>
          </div>

          <!-- ROW M -->
          <div class="size-row-item" style="display: flex !important; justify-content: space-between; align-items: center; background: white; padding: 10px 15px; border-radius: 10px; border: 1px solid #cbd5e1;">
            <div style="font-weight: 900; font-size: 1.1rem; color: #0f172a; width: 40px;">M</div>
            <div class="quantity-controller" style="display: flex; align-items: center; gap: 12px;">
              <button type="button" (click)="decrementStock('M')" style="width: 36px; height: 36px; border-radius: 50%; border: 2px solid #ef4444; background: white; color: #ef4444; font-size: 1.1rem; cursor: pointer; font-weight: 900;">-</button>
              <input type="number" [(ngModel)]="sizeInputs['M']" min="0" style="width: 60px; height: 40px; text-align: center; font-size: 1.3rem; font-weight: 900; border: none; background: #f1f5f9; border-radius: 8px; color: #1e293b;" />
              <button type="button" (click)="incrementStock('M')" style="width: 36px; height: 36px; border-radius: 50%; border: 2px solid #10b981; background: white; color: #10b981; font-size: 1.1rem; cursor: pointer; font-weight: 900;">+</button>
            </div>
          </div>

          <!-- ROW L -->
          <div class="size-row-item" style="display: flex !important; justify-content: space-between; align-items: center; background: white; padding: 10px 15px; border-radius: 10px; border: 1px solid #cbd5e1;">
            <div style="font-weight: 900; font-size: 1.1rem; color: #0f172a; width: 40px;">L</div>
            <div class="quantity-controller" style="display: flex; align-items: center; gap: 12px;">
              <button type="button" (click)="decrementStock('L')" style="width: 36px; height: 36px; border-radius: 50%; border: 2px solid #ef4444; background: white; color: #ef4444; font-size: 1.1rem; cursor: pointer; font-weight: 900;">-</button>
              <input type="number" [(ngModel)]="sizeInputs['L']" min="0" style="width: 60px; height: 40px; text-align: center; font-size: 1.3rem; font-weight: 900; border: none; background: #f1f5f9; border-radius: 8px; color: #1e293b;" />
              <button type="button" (click)="incrementStock('L')" style="width: 36px; height: 36px; border-radius: 50%; border: 2px solid #10b981; background: white; color: #10b981; font-size: 1.1rem; cursor: pointer; font-weight: 900;">+</button>
            </div>
          </div>

          <!-- ROW XL -->
          <div class="size-row-item" style="display: flex !important; justify-content: space-between; align-items: center; background: white; padding: 10px 15px; border-radius: 10px; border: 1px solid #cbd5e1;">
            <div style="font-weight: 900; font-size: 1.1rem; color: #0f172a; width: 40px;">XL</div>
            <div class="quantity-controller" style="display: flex; align-items: center; gap: 12px;">
              <button type="button" (click)="decrementStock('XL')" style="width: 36px; height: 36px; border-radius: 50%; border: 2px solid #ef4444; background: white; color: #ef4444; font-size: 1.1rem; cursor: pointer; font-weight: 900;">-</button>
              <input type="number" [(ngModel)]="sizeInputs['XL']" min="0" style="width: 60px; height: 40px; text-align: center; font-size: 1.3rem; font-weight: 900; border: none; background: #f1f5f9; border-radius: 8px; color: #1e293b;" />
              <button type="button" (click)="incrementStock('XL')" style="width: 36px; height: 36px; border-radius: 50%; border: 2px solid #10b981; background: white; color: #10b981; font-size: 1.1rem; cursor: pointer; font-weight: 900;">+</button>
            </div>
          </div>

          <!-- ROW XXL -->
          <div class="size-row-item" style="display: flex !important; justify-content: space-between; align-items: center; background: white; padding: 10px 15px; border-radius: 10px; border: 1px solid #cbd5e1;">
            <div style="font-weight: 900; font-size: 1.1rem; color: #0f172a; width: 40px;">XXL</div>
            <div class="quantity-controller" style="display: flex; align-items: center; gap: 12px;">
              <button type="button" (click)="decrementStock('XXL')" style="width: 36px; height: 36px; border-radius: 50%; border: 2px solid #ef4444; background: white; color: #ef4444; font-size: 1.1rem; cursor: pointer; font-weight: 900;">-</button>
              <input type="number" [(ngModel)]="sizeInputs['XXL']" min="0" style="width: 60px; height: 40px; text-align: center; font-size: 1.3rem; font-weight: 900; border: none; background: #f1f5f9; border-radius: 8px; color: #1e293b;" />
              <button type="button" (click)="incrementStock('XXL')" style="width: 36px; height: 36px; border-radius: 50%; border: 2px solid #10b981; background: white; color: #10b981; font-size: 1.1rem; cursor: pointer; font-weight: 900;">+</button>
            </div>
          </div>

        </div>

        <div style="display: flex; gap: 15px; margin-top: 30px;">
          <button
            type="button"
            class="btn-confirm-save-premium"
            (click)="submitStock()"
            [disabled]="submitting"
            style="flex: 2; background: #10b981; color: white; height: 60px; border-radius: 15px; font-weight: 900; font-size: 1.2rem; border: none; cursor: pointer;"
          >
            <i class="fas fa-save" *ngIf="!submitting"></i>
            {{ submitting ? 'GUARDANDO...' : 'GUARDAR TODO' }}
          </button>
        </div>
      </div>
    </div>

    <!-- FOOTER CANCEL -->
    <div class="form-actions" style="margin-top: 2rem;" *ngIf="currentStep === 1">
      <button type="button" class="btn btn-secondary" (click)="cancel()" style="width: 100%; height: 45px; border-radius: 10px;">
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

  currentStep: any = 1;
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

  incrementStock(size: string) {
    if (this.sizeInputs[size] === undefined) this.sizeInputs[size] = 0;
    this.sizeInputs[size]++;
    this.cdr.detectChanges();
  }

  decrementStock(size: string) {
    if (this.sizeInputs[size] === undefined) this.sizeInputs[size] = 0;
    if (this.sizeInputs[size] > 0) {
      this.sizeInputs[size]--;
      this.cdr.detectChanges();
    }
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
