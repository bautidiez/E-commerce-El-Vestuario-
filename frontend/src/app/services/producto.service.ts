import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { tap, map } from 'rxjs/operators';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ProductoService {
  private apiUrl = `${environment.apiUrl}/productos`;
  private productosCache = new BehaviorSubject<any[]>([]);
  public productos$ = this.productosCache.asObservable();
  private cargado = false;
  private totalProductos = 0;

  constructor(private http: HttpClient) {}

  /**
   * Carga todos los productos en memoria (una sola vez)
   * Ideal para el catálogo inicial y búsquedas rápidas
   */
  cargarProductos(): Observable<any[]> {
    // Si ya está cargado, retornar el observable del BehaviorSubject
    if (this.cargado) {
      return of(this.productosCache.value);
    }

    return this.http.get<any>(this.apiUrl)
      .pipe(
        tap(response => {
          // El backend puede devolver {productos: [], total: X} o {items: [], total: X}
          const productos = response.productos || response.items || [];
          this.productosCache.next(productos);
          this.totalProductos = response.total || productos.length;
          this.cargado = true;
          console.log('✅ Productos precargados en RAM:', productos.length);
        }),
        map(response => response.productos || response.items || [])
      );
  }

  /**
   * Obtiene productos filtrados desde el cache local
   */
  buscarEnCache(termino: string): any[] {
    const productos = this.productosCache.value;
    if (!termino) return productos;
    
    termino = termino.toLowerCase();
    return productos.filter(p => 
      p.nombre.toLowerCase().includes(termino) || 
      (p.categoria_nombre && p.categoria_nombre.toLowerCase().includes(termino))
    );
  }

  /**
   * Forzar recarga de productos
   */
  refrescarProductos(): Observable<any[]> {
    this.cargado = false;
    return this.cargarProductos();
  }
}
