import { Component, ChangeDetectorRef, NgZone, HostListener, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Router, ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { RecaptchaModule } from 'ng-recaptcha';
import Swal from 'sweetalert2';

import { GoogleAuthService } from '../../services/google-auth.service';

@Component({
    selector: 'app-registro',
    standalone: true,
    imports: [CommonModule, FormsModule, RouterLink, RecaptchaModule],
    templateUrl: './registro.html',
    styleUrl: './registro.css'
})
export class RegistroComponent implements OnInit {
    cliente = {
        nombre: '',
        email: '',
        password: '',
        telefono: '',
        metodo_verificacion: 'email',
        acepta_newsletter: true,
        recaptcha_token: ''
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

    registrando = false;
    mensajeExito = false;
    mensajeError = '';
    esperandoVerificacion = false;
    codigoVerificacion = '';
    verificando = false;

    constructor(
        private apiService: ApiService,
        private authService: AuthService,
        private googleAuthService: GoogleAuthService,
        private router: Router,
        private route: ActivatedRoute,
        private cdr: ChangeDetectorRef,
        private zone: NgZone
    ) {
        this.route.queryParams.subscribe(params => {
            if (params['email'] && params['verify']) {
                this.cliente.email = params['email'];
                this.esperandoVerificacion = true;
            }
        });
    }

    ngOnInit() {
        // Restaurar estado si existe en localStorage (para recargas accidentales en móvil)
        const savedState = localStorage.getItem('pending_registration');
        if (savedState) {
            try {
                const data = JSON.parse(savedState);
                if (data.email && data.esperando) {
                    this.cliente.email = data.email;
                    this.cliente.metodo_verificacion = data.metodo || 'telefono';
                    this.esperandoVerificacion = true;
                    console.log('DEBUG REGISTRO: Estado restaurado para', data.email);
                }
            } catch (e) {
                localStorage.removeItem('pending_registration');
            }
        }
    }

    loginConGoogle() {
        this.googleAuthService.loginWithGoogle();
    }

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

    // CAPTCHA RESOLVED
    onCaptchaResolved(token: string | null) {
        this.cliente.recaptcha_token = token || '';
        console.log('DEBUG REGISTRO: Captcha resolved', token ? 'OK' : 'NULL');
    }

    // Validar email
    validarEmail(email: string): boolean {
        const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return regex.test(email);
    }

    // Validar teléfono (más flexible)
    validarTelefono(telefono: string): boolean {
        const telefonoLimpio = telefono.replace(/[\s-().]/g, '');
        // Al menos 8 dígitos, permite prefijos internacionales opcionales
        return telefonoLimpio.length >= 8 && /^\+?\d+$/.test(telefonoLimpio);
    }

    // Validar contraseña compleja
    validarPassword(password: string): boolean {
        // Al menos 8 caracteres, una mayúscula, una minúscula y un número
        const regex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;
        return regex.test(password);
    }

    registrar() {
        if (!this.cliente.nombre || !this.cliente.email || !this.cliente.password || !this.cliente.telefono) {
            this.mensajeError = 'Por favor completa todos los campos';
            return;
        }

        if (!this.validarEmail(this.cliente.email)) {
            this.mensajeError = 'Por favor ingresa un email válido';
            return;
        }

        if (!this.validarTelefono(this.cliente.telefono)) {
            this.mensajeError = 'Por favor ingresa un teléfono válido';
            return;
        }

        if (!this.validarPassword(this.cliente.password)) {
            this.mensajeError = 'La contraseña debe tener al menos 8 caracteres, incluir una mayúscula, una minúscula y un número';
            return;
        }

        // Validate CAPTCHA
        if (!this.cliente.recaptcha_token) {
            this.mensajeError = 'Por favor completa el captcha';
            return;
        }

        this.registrando = true;
        this.mensajeError = '';

        // Combinar prefijo con teléfono para el envío
        const clienteParaEnviar = {
            ...this.cliente,
            telefono: `${this.prefijoTelefono} ${this.cliente.telefono}`,
            recaptcha_token: this.cliente.recaptcha_token
        };

        console.log('DEBUG REGISTRO: Enviando datos', clienteParaEnviar);

        this.apiService.registrarCliente(clienteParaEnviar).subscribe({
            next: (res) => {
                console.log('DEBUG REGISTRO: Registro exitoso', res);
                this.zone.run(() => {
                    // Guardar estado en localStorage
                    localStorage.setItem('pending_registration', JSON.stringify({
                        email: this.cliente.email,
                        metodo: this.cliente.metodo_verificacion,
                        esperando: true
                    }));

                    this.esperandoVerificacion = true;
                    this.registrando = false;
                    this.cdr.detectChanges();
                });
            },
            error: (error: any) => {
                console.error('DEBUG REGISTRO: Error en registro', error);
                this.zone.run(() => {
                    this.mensajeError = error.error?.error || 'Error al registrar. Intenta nuevamente.';
                    this.registrando = false;
                    this.cdr.detectChanges();
                });
            }
        });
    }

    verificarCodigo() {
        if (!this.codigoVerificacion || this.codigoVerificacion.length !== 6) {
            this.mensajeError = 'El código debe ser de 6 dígitos';
            return;
        }

        this.verificando = true;
        this.mensajeError = '';

        const codigoLimpio = this.codigoVerificacion.trim();

        this.apiService.verificarCodigo(this.cliente.email, codigoLimpio).subscribe({
            next: (response: any) => {
                this.zone.run(() => {
                    localStorage.removeItem('pending_registration');
                    this.mensajeExito = true;
                    this.verificando = false;

                    // Auto-login
                    if (response.access_token) {
                        this.authService.setSession(response, 'cliente');
                    }

                    this.cdr.detectChanges();

                    setTimeout(() => {
                        this.router.navigate(['/']); // Redirigir al inicio o a donde el usuario estaba
                    }, 1500);
                });
            },
            error: (error) => {
                this.zone.run(() => {
                    this.mensajeError = error.error?.error || 'Código incorrecto';
                    this.verificando = false;
                    this.cdr.detectChanges();
                });
            }
        });
    }

    reenviarCodigo() {
        this.apiService.reenviarCodigo(this.cliente.email).subscribe({
            next: () => {
                Swal.fire('Éxito', 'Código reenviado. Revisa tu email.', 'success');
            }
        });
    }
}
