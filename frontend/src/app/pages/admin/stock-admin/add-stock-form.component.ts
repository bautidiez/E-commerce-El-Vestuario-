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
  template: `
    <div class="add-stock-form" style="min-height: 500px !important; background: white !important; display: block !important; width: 100% !important; border: 5px solid #000 !important; padding: 20px !important; position: relative !important; z-index: 9999 !important;">
      
      <!-- DEBUG BAR -->
      <div style="background: #000; color: #fff; padding: 5px 15px; font-weight: 800; font-size: 12px; margin-bottom: 20px; border-radius: 5px; display: flex; justify-content: space-between;">
        <span>MODO ADMINISTRADOR: GESTIÓN DE STOCK</span>
        <span>PASO ACTUAL: {{ currentStep }} | SELECCIONADOS: {{ selectedProducts.length }}</span>
      </div>

      <!-- STEP 1: SELECCIÓN -->
      <div [hidden]="currentStep !== 1" style="display: block !important;">
        <div class="product-search-container" style="background: #f8fafc; padding: 20px; border-radius: 12px; border: 2px solid #6366f1; margin-bottom: 20px;">
          <h4 style="margin: 0 0 15px 0; color: #0f172a; font-weight: 800;">1. BUSCAR PRODUCTOS</h4>
          <div style="position: relative;">
            <input
              type="text"
              class="form-control"
              [(ngModel)]="searchQuery"
              (input)="onSearchInput($event)"
              placeholder="Escribe el nombre de la camiseta..."
              style="width: 100%; padding: 15px; border-radius: 10px; border: 2px solid #cbd5e1; font-size: 1.1rem;"
            />
            
            <!-- SEARCH RESULTS -->
            <div class="search-results shadow-2xl" *ngIf="searchResults.length > 0" style="position: absolute; top: 100%; left: 0; right: 0; background: white; z-index: 10000; border: 2px solid #cbd5e1; border-radius: 0 0 12px 12px; max-height: 300px; overflow-y: auto;">
              <div *ngFor="let product of searchResults" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; border-bottom: 1px solid #f1f5f9;">
                <div>
                  <div style="font-weight: 800; color: #1e293b;">{{ product.nombre }}</div>
                  <div style="font-size: 0.8rem; color: #4338ca; font-weight: 700; text-transform: uppercase;">{{ product.version || 'No Definida' }}</div>
                </div>
                <button (click)="selectProduct(product)" style="background: #000; color: white; border: none; padding: 8px 15px; border-radius: 8px; font-weight: 800; cursor: pointer;">
                  AÑADIR
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="selected-area" *ngIf="selectedProducts.length > 0">
          <h4 style="font-weight: 800; color: #0f172a; margin: 25px 0 15px 0;">LISTA DE SELECCIÓN</h4>
          <div *ngFor="let prod of selectedProducts; let i = index" style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 15px 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 10px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
            <div>
              <div style="font-weight: 800;">{{ prod.nombre }}</div>
              <div style="font-size: 0.8rem; color: #64748b;">{{ prod.version }}</div>
            </div>
            <button (click)="removeProduct(i)" style="background: #fee2e2; color: #ef4444; border: 1px solid #fecaca; padding: 6px 12px; border-radius: 8px; font-weight: 800; cursor: pointer;">
              QUITAR
            </button>
          </div>
          
          <button (click)="nextStep()" style="width: 100%; height: 60px; background: #000; color: white; border: none; border-radius: 12px; font-weight: 800; font-size: 1.1rem; margin-top: 20px; cursor: pointer; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);">
            SIGUIENTE: CARGAR STOCK <i class="fas fa-chevron-right"></i>
          </button>
        </div>
      </div>

      <!-- STEP 2: CARGA DE STOCK -->
      <div [hidden]="currentStep !== 2" style="display: block !important;">
        <div style="background: #fff; padding: 30px; border-radius: 18px; border: 3px solid #10b981; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1);">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 30px;">
            <div style="text-align: left;">
              <h3 style="font-weight: 900; color: #1e293b; margin: 0; font-size: 1.5rem;">Cargar Unidades</h3>
              <p style="color: #64748b; font-weight: 700; margin: 5px 0;">Sumar stock a {{ selectedProducts.length }} camisetas</p>
            </div>
            <button (click)="prevStep()" style="background: #f1f5f9; border: 1px solid #e2e8f0; padding: 8px 15px; border-radius: 8px; color: #4338ca; font-weight: 800; cursor: pointer;">
              <i class="fas fa-arrow-left"></i> VOLVER
            </button>
          </div>

          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; background: #f8fafc; padding: 25px; border-radius: 15px; border: 1px solid #cbd5e1;">
            <div *ngFor="let size of sizes" style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
              <label style="font-weight: 900; color: #1e293b; font-size: 1.1rem;">{{ size }}</label>
              <input
                type="number"
                [(ngModel)]="sizeInputs[size]"
                style="width: 100%; height: 60px; text-align: center; font-size: 1.5rem; font-weight: 900; border: 3px solid #cbd5e1; border-radius: 12px; background: white;"
              />
            </div>
          </div>

          <button (click)="submitStock()" [disabled]="submitting" style="width: 100%; height: 70px; background: #10b981; color: white; border: none; border-radius: 15px; font-weight: 900; font-size: 1.3rem; margin-top: 30px; cursor: pointer; box-shadow: 0 20px 25px -5px rgba(16, 185, 129, 0.3);">
            {{ submitting ? 'GUARDANDO...' : 'CONFIRMAR Y GUARDAR' }}
          </button>
        </div>
      </div>

      <div *ngIf="selectedProducts.length === 0 && currentStep === 1" style="padding: 40px; text-align: center; color: #94a3b8;">
        <i class="fas fa-tshirt" style="font-size: 3rem; margin-bottom: 15px; display: block; opacity: 0.2;"></i>
        <p style="font-weight: 700;">Busca camisetas arriba para empezar.</p>
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
