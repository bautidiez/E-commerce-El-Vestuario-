import { Component, Input, ChangeDetectorRef } from '@angular/core';
import { CommonModule, Location } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { PickupPointsModalComponent, PuntoRetiro } from '../pickup-points-modal/pickup-points-modal';

@Component({
    selector: 'app-shipping-calculator',
    standalone: true,
    imports: [CommonModule, FormsModule, PickupPointsModalComponent],
    templateUrl: './shipping-calculator.html',
    styleUrl: './shipping-calculator.css'
})
export class ShippingCalculatorComponent {
    @Input() precioBase: number = 0;
    @Input() items: any[] = [];

    codigoPostal: string = '';
    codigoPostalCalculado: string = ''; // CP actualmente calculado
    calculando: boolean = false;
    opcionesEnvio: any[] = [];
    error: string = '';
    mostrarResultados: boolean = false;
    mostrarTodasOpciones: boolean = false; // Para toggle "Ver más/menos"
    editandoCodigoPostal: boolean = false; // Para mostrar/ocultar campo de cambio

    // Modal de puntos de retiro
    mostrarModalPuntos: boolean = false;
    puntosRetiro: PuntoRetiro[] = [];
    carrierSeleccionado: string = '';

    constructor(
        private apiService: ApiService,
        private location: Location,
        private cdr: ChangeDetectorRef
    ) {
        // Recuperar CP de localStorage si existe
        const savedCP = localStorage.getItem('codigo_postal');
        if (savedCP) {
            this.codigoPostal = savedCP;
        }
    }

    volver(): void {
        this.location.back();
    }

    calcular() {
        if (!this.codigoPostal || this.codigoPostal.length < 4) {
            this.error = 'Por favor ingresa un código postal válido';
            return;
        }

        this.calculando = true;
        this.error = '';
        this.opcionesEnvio = [];

        // Guardar CP
        localStorage.setItem('codigo_postal', this.codigoPostal);

        // Llamar a la API una sola vez para obtener todo
        this.apiService.calcularEnvio({
            codigo_postal: this.codigoPostal,
            provincia: '', // Opcional
            items: this.items
        }).subscribe({
            next: (res) => {
                const options = Array.isArray(res) ? res : [res];

                this.opcionesEnvio = options.map(opt => ({
                    id: opt.id,
                    nombre: opt.nombre,
                    costo: opt.costo,
                    tiempo: opt.tiempo_estimado || opt.tiempo || '3-5 días hábiles'
                }));

                // Asegurar que "Retiro en Local" esté presente si no vino de la API
                if (!this.opcionesEnvio.find(o => o.id.includes('retiro'))) {
                    this.opcionesEnvio.push({
                        id: 'retiro_local',
                        nombre: 'Retiro en local',
                        costo: 0,
                        tiempo: 'Inmediato'
                    });
                }

                this.calculando = false;
                this.mostrarResultados = true;
                this.codigoPostalCalculado = this.codigoPostal;
                this.editandoCodigoPostal = false;
                this.cdr.detectChanges();
            },
            error: (err) => {
                console.error('Error calculando envío:', err);
                this.error = 'Hubo un error al calcular los envíos. Por favor intenta más tarde.';
                this.calculando = false;
            }
        });
    }

    private checkFinalizacion(current: number, total: number) {
        if (current === total) {
            this.calculando = false;
            this.mostrarResultados = true;
            this.codigoPostalCalculado = this.codigoPostal;
            this.editandoCodigoPostal = false;
            // Ordenar por costo
            this.opcionesEnvio.sort((a, b) => a.costo - b.costo);
            // Forzar detección de cambios para mostrar resultados inmediatamente
            this.cdr.detectChanges();
        }
    }

    private getNombreMetodo(id: string): string {
        const nombres: any = {
            'correo_argentino': 'Correo Argentino',
            'andreani': 'Andreani'
        };
        return nombres[id] || id;
    }

    getPrecioConTransferencia(costoEnvio: number): number {
        // Ejemplo: 15% de descuento por transferencia sobre el total
        const total = this.precioBase + costoEnvio;
        return total * 0.85;
    }

    cambiarCodigoPostal() {
        this.editandoCodigoPostal = true;
        this.codigoPostalCalculado = '';
        this.mostrarResultados = false;
        this.codigoPostal = '';
    }

    cerrarResultados() {
        this.mostrarResultados = false;
    }

    toggleOpciones() {
        this.mostrarTodasOpciones = !this.mostrarTodasOpciones;
    }

    getOpcionesDomicilio() {
        return this.opcionesEnvio.filter(o => {
            const name = o.nombre.toLowerCase();
            const isHomeKeyword = name.includes('domicilio') || name.includes('estándar') || name.includes('envío');
            const isPickupKeyword = name.includes('sucursal') || name.includes('retiro') || name.includes('local');
            return isHomeKeyword && !isPickupKeyword;
        });
    }

    getOpcionesRetiro() {
        return this.opcionesEnvio.filter(o => {
            const name = o.nombre.toLowerCase();
            return name.includes('sucursal') || name.includes('retiro') || name.includes('local');
        });
    }

    verPuntosRetiro(carrier: string) {
        this.carrierSeleccionado = carrier;
        // Fetch pickup points from API
        this.apiService.getPuntosRetiro(carrier, this.codigoPostalCalculado).subscribe({
            next: (puntos: PuntoRetiro[]) => {
                this.puntosRetiro = puntos;
                this.mostrarModalPuntos = true;
            },
            error: (err: any) => {
                console.error('Error fetching pickup points:', err);
                // Show modal anyway with empty list
                this.puntosRetiro = [];
                this.mostrarModalPuntos = true;
            }
        });
    }

    cerrarModalPuntos() {
        this.mostrarModalPuntos = false;
    }

    seleccionarPunto(punto: PuntoRetiro) {
        console.log('Punto seleccionado:', punto);
        // Aquí puedes almacenar el punto seleccionado
    }
}
