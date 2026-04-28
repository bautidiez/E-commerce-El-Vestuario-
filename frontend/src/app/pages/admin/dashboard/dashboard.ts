import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { AuthService } from '../../../services/auth.service';
import { ApiService } from '../../../services/api.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})

export class DashboardComponent implements OnInit {
  estadisticas: any = null;
  estadisticasVentas: any = null;
  loading = true;
  loadingVentas = false;
  isAuthenticated = false;
  errorMessage = ''; // Para mostrar el error en pantalla
  periodoSeleccionado = 'dia'; // dia, semana, mes, anio
  periodoGananciaSeleccionado: 'hoy' | 'semana' | 'mes' | 'todo' = 'todo';

  // Navegación para estadísticas
  semanaOffset = 0; // Cuántos bloques de 8 semanas retroceder
  anioSemanas = new Date().getFullYear(); // Año para vista de semanas
  anioMeses = new Date().getFullYear(); // Año para vista de meses

  // Variables antiguas (mantener por compatibilidad)
  anioSeleccionado = new Date().getFullYear();
  mesSeleccionado = new Date().getMonth() + 1;
  aniosDisponibles: number[] = [];
  mesesDisponibles = [
    { id: 1, nombre: 'Enero' }, { id: 2, nombre: 'Febrero' }, { id: 3, nombre: 'Marzo' },
    { id: 4, nombre: 'Abril' }, { id: 5, nombre: 'Mayo' }, { id: 6, nombre: 'Junio' },
    { id: 7, nombre: 'Julio' }, { id: 8, nombre: 'Agosto' }, { id: 9, nombre: 'Septiembre' },
    { id: 10, nombre: 'Octubre' }, { id: 11, nombre: 'Noviembre' }, { id: 12, nombre: 'Diciembre' }
  ];

  currentDate = new Date(); // Fecha de referencia para la navegación

  constructor(
    private authService: AuthService,
    private apiService: ApiService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) { }

  ngOnInit() {
    // Verificar autenticación de forma síncrona primero
    if (!this.authService.isLoggedIn()) {
      this.router.navigate(['/admin/login']);
      return;
    }

    this.isAuthenticated = true;
    this.generarAniosDisponibles();
    this.loadEstadisticas();
    this.loadEstadisticasVentas();

    // Suscribirse para cambios futuros
    this.authService.isAuthenticated$.subscribe(isAuth => {
      this.isAuthenticated = isAuth;
      if (!isAuth) {
        this.router.navigate(['/admin/login']);
      }
    });
  }

  loadEstadisticas() {
    // No mostrar loading si ya hay datos
    if (!this.estadisticas) {
      this.loading = true;
    }
    this.apiService.getEstadisticas().subscribe({
      next: (data) => {
        this.estadisticas = data;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Error cargando estadísticas:', error);
        this.loading = false;

        if (error.status === 500) {
          this.errorMessage = `Error del servidor: ${error.error?.error || error.message || 'Desconocido'}`;
        } else {
          this.errorMessage = `Error de conexión: ${error.status} ${error.statusText}`;
        }

        this.cdr.detectChanges();
      }
    });
  }

  loadEstadisticasVentas() {
    this.loadingVentas = true;
    let semanaOffset: number | undefined = undefined;
    let anio: number | undefined = undefined;

    // Configurar parámetros según el periodo
    if (this.periodoSeleccionado === 'mes') {
      anio = this.anioMeses;
    }

    const fechaRefStr = this.currentDate.toISOString().split('T')[0];

    this.apiService.getEstadisticasVentas(this.periodoSeleccionado, semanaOffset, anio, fechaRefStr).subscribe({
      next: (data) => {
        this.estadisticasVentas = data;
        this.loadingVentas = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Error cargando estadísticas de ventas:', error);
        this.loadingVentas = false;
        this.estadisticasVentas = null;
        this.cdr.detectChanges();
      }
    });
  }

  cambiarPeriodo(periodo: string) {
    this.periodoSeleccionado = periodo;

    // Resetear offset y año al cambiar de periodo
    this.semanaOffset = 0;
    this.anioSemanas = new Date().getFullYear();
    this.anioMeses = new Date().getFullYear();
    this.currentDate = new Date();

    this.loadEstadisticasVentas();
  }

  paginarAtras() {
    if (this.periodoSeleccionado === 'dia') {
      // Día a día: retroceder 1 semana
      this.currentDate.setDate(this.currentDate.getDate() - 7);
    } else if (this.periodoSeleccionado === 'semana') {
      // Semana: retroceder 8 semanas
      this.currentDate.setDate(this.currentDate.getDate() - (7 * 8));
    } else if (this.periodoSeleccionado === 'mes') {
      // Mes: retroceder 1 año
      this.anioMeses--;
    }
    // Año: no hay navegación hacia atrás

    this.loadEstadisticasVentas();
  }

  paginarAdelante() {
    const hoy = new Date();
    const añoActual = hoy.getFullYear();

    if (this.periodoSeleccionado === 'dia') {
      // Día a día: avanzar 1 semana
      this.currentDate.setDate(this.currentDate.getDate() + 7);
      if (this.currentDate > hoy) this.currentDate = hoy;
    } else if (this.periodoSeleccionado === 'semana') {
      // Semana: avanzar 8 semanas
      this.currentDate.setDate(this.currentDate.getDate() + (7 * 8));
      if (this.currentDate > hoy) this.currentDate = hoy;
    } else if (this.periodoSeleccionado === 'mes') {
      // Mes: avanzar 1 año
      if (this.anioMeses < añoActual) {
        this.anioMeses++;
      }
    }

    this.loadEstadisticasVentas();
  }

  generarAniosDisponibles() {
    const anioActual = new Date().getFullYear();
    // Generar años desde 2024 hasta el actual
    for (let a = 2024; a <= anioActual; a++) {
      if (!this.aniosDisponibles.includes(a)) {
        this.aniosDisponibles.push(a);
      }
    }
  }

  logout() {
    this.authService.logout();
  }

  goToPanelGestion() {
    this.router.navigate(['/admin/gestion']);
  }

  goToGestionProductos() {
    this.router.navigate(['/admin/productos']);
  }

  goToGestionCategorias() {
    this.router.navigate(['/admin/categorias']);
  }

  goToGestionPedidos() {
    this.router.navigate(['/admin/pedidos']);
  }

  goToGestionStock() {
    this.router.navigate(['/admin/stock']);
  }

  goToGestionPromociones() {
    this.router.navigate(['/admin/promociones']);
  }

  goToGestionNewsletter() {
    this.router.navigate(['/admin/newsletter']);
  }

  getVentaMaxima(): any {
    if (!this.estadisticasVentas || !this.estadisticasVentas.datos) return null;
    return this.estadisticasVentas.datos.reduce((max: any, item: any) =>
      item.ventas > max.ventas ? item : max, this.estadisticasVentas.datos[0]);
  }

  getVentaMinima(): any {
    if (!this.estadisticasVentas || !this.estadisticasVentas.datos) return null;
    return this.estadisticasVentas.datos.reduce((min: any, item: any) =>
      item.ventas < min.ventas ? item : min, this.estadisticasVentas.datos[0]);
  }
}
