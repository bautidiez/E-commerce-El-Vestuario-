import { Component, OnInit, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-encargo-especial',
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './encargo-especial.html',
  styleUrl: './encargo-especial.css'
})
export class EncargoEspecialComponent implements OnInit {
  categorias: any[] = [];
  talles: any[] = [];

  encargo = {
    categoria_id: null as number | null,
    club: '',
    numero: null as number | null,
    dorsal: '',
    talle: null as number | null,
    color: '',
    observaciones: '',
    nombre_cliente: '',
    email_cliente: '',
    telefono_cliente: ''
  };

  prefijos = [
    { nombre: 'Argentina', codigo: '+54 9', flag: '🇦🇷', iso: 'ar' },
    { nombre: 'Uruguay', codigo: '+598', flag: '🇺🇾', iso: 'uy' },
    { nombre: 'Chile', codigo: '+56', flag: '🇨🇱', iso: 'cl' },
    { nombre: 'Paraguay', codigo: '+595', flag: '🇵🇾', iso: 'py' },
    { nombre: 'Bolivia', codigo: '+591', flag: '🇧🇴', iso: 'bo' },
    { nombre: 'Brasil', codigo: '+55', flag: '🇧🇷', iso: 'br' },
    { nombre: 'Perú', codigo: '+51', flag: '🇵🇪', iso: 'pe' },
    { nombre: 'Ecuador', codigo: '+593', flag: '🇪🇨', iso: 'ec' },
    { nombre: 'Colombia', codigo: '+57', flag: '🇨🇴', iso: 'co' },
    { nombre: 'Venezuela', codigo: '+58', flag: '🇻🇪', iso: 've' },
    { nombre: 'México', codigo: '+52', flag: '🇲🇽', iso: 'mx' },
    { nombre: 'España', codigo: '+34', flag: '🇪🇸', iso: 'es' },
    { nombre: 'USA', codigo: '+1', flag: '🇺🇸', iso: 'us' }
  ];

  prefijoTelefono = '+54 9';
  dropdownAbierto = false;
  enviando = false;
  mensajeExito = false;
  mensajeError = '';

  constructor(private apiService: ApiService) { }

  @HostListener('document:click', ['$event'])
  onClickDocument(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (!target.closest('.custom-prefix-selector')) {
      this.dropdownAbierto = false;
    }
  }

  toggleDropdown() {
    this.dropdownAbierto = !this.dropdownAbierto;
  }

  seleccionarPrefijo(codigo: string) {
    this.prefijoTelefono = codigo;
    this.dropdownAbierto = false;
  }

  getPrefijoActual() {
    return this.prefijos.find(p => p.codigo === this.prefijoTelefono) || this.prefijos[0];
  }

  ngOnInit() {
    this.loadCategorias();
    this.loadTalles();
  }

  loadCategorias() {
    // Pedir lista plana para facilitar la selección directa
    this.apiService.getCategorias(true).subscribe({
      next: (data: any) => {
        this.categorias = data.sort((a: any, b: any) => a.nombre.localeCompare(b.nombre));
        console.log('Categorías cargadas:', this.categorias);
      },
      error: (error: any) => {
        console.error('Error cargando categorías:', error);
      }
    });
  }

  loadTalles() {
    this.apiService.getTalles().subscribe({
      next: (data: any) => {
        this.talles = data;
      },
      error: (error: any) => {
        console.error('Error cargando talles:', error);
      }
    });
  }

  // Validar email
  validarEmail(email: string): boolean {
    const regex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return regex.test(email);
  }

  // Validar teléfono
  validarTelefono(telefono: string): boolean {
    // Si es argentina (+54 9), debe tener 10 dígitos después del prefijo
    if (this.prefijoTelefono === '+54 9') {
      const limpio = telefono.replace(/\D/g, '');
      return limpio.length >= 8 && limpio.length <= 11;
    }
    return telefono.length >= 6;
  }

  enviarEncargo() {
    // Validaciones
    if (!this.encargo.nombre_cliente || !this.encargo.email_cliente || !this.encargo.telefono_cliente) {
      this.mensajeError = 'Por favor completa tus datos de contacto';
      return;
    }

    if (!this.validarEmail(this.encargo.email_cliente)) {
      this.mensajeError = 'El formato del email no es válido';
      return;
    }

    if (!this.validarTelefono(this.encargo.telefono_cliente)) {
      this.mensajeError = 'El número de teléfono parece incorrecto';
      return;
    }

    if (!this.encargo.categoria_id || !this.encargo.club || !this.encargo.talle) {
      this.mensajeError = 'Por favor selecciona categoría, indica el club/país y selecciona un talle';
      return;
    }

    this.enviando = true;
    this.mensajeError = '';

    // Usar == para evitar problemas si uno es string y el otro number
    const categoria = this.categorias.find(c => c.id == this.encargo.categoria_id);
    const categoriaNombre = categoria?.nombre || 'No especificada';

    const talleObj = this.talles.find(t => t.id == this.encargo.talle);
    const talleNombre = talleObj?.nombre || 'No especificado';

    const telefonoCompleto = `${this.prefijoTelefono}${this.encargo.telefono_cliente}`;

    // Enviar por WhatsApp
    const mensaje = `🎯 ENCARGO ESPECIAL\n\n` +
      `Categoría: ${categoriaNombre}\n` +
      `Club/País: ${this.encargo.club}\n` +
      `Número: ${this.encargo.numero || 'No especificado'}\n` +
      `Dorsal: ${this.encargo.dorsal || 'No especificado'}\n` +
      `Talle: ${talleNombre}\n` +
      `Color: ${this.encargo.color || 'No especificado'}\n` +
      `Observaciones: ${this.encargo.observaciones || 'Ninguna'}\n\n` +
      `👤 DATOS DEL CLIENTE\n` +
      `Nombre: ${this.encargo.nombre_cliente}\n` +
      `Email: ${this.encargo.email_cliente}\n` +
      `Teléfono: ${telefonoCompleto}`;

    const whatsappUrl = `https://wa.me/5493584171716?text=${encodeURIComponent(mensaje)}`;
    window.open(whatsappUrl, '_blank');

    setTimeout(() => {
      this.enviando = false;
      this.mensajeExito = true;
      setTimeout(() => {
        this.mensajeExito = false;
        this.resetForm();
      }, 3000);
    }, 1000);
  }

  resetForm() {
    this.encargo = {
      categoria_id: null,
      club: '',
      numero: null,
      dorsal: '',
      talle: null,
      color: '',
      observaciones: '',
      nombre_cliente: '',
      email_cliente: '',
      telefono_cliente: ''
    };
    this.prefijoTelefono = '+54 9';
  }
}
