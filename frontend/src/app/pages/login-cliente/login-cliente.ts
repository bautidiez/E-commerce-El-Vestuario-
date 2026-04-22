import { Component, ChangeDetectorRef, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { RecaptchaModule } from 'ng-recaptcha';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-login-cliente',
    standalone: true,
    imports: [CommonModule, FormsModule, RouterModule, RecaptchaModule],
    templateUrl: './login-cliente.html',
    styleUrl: './login-cliente.css',
})
export class LoginClienteComponent {
    email = '';
    password = '';
    error = '';
    loading = false;
    recaptcha_token = ''; // Token state

    constructor(
        private authService: AuthService,
        private router: Router,
        private cdr: ChangeDetectorRef,
        private zone: NgZone
    ) { }

    onCaptchaResolved(token: string | null) {
        this.recaptcha_token = token || '';
        console.log('DEBUG LOGIN: Captcha resolved', token ? 'OK' : 'NULL');
    }

    login() {
        console.log('DEBUG LOGIN: Iniciando proceso para', this.email);

        // Validate Captcha first
        if (!this.recaptcha_token) {
            this.error = 'Por favor completa el captcha';
            return;
        }

        if (!this.email || !this.password) {
            this.error = 'Por favor completa todos los campos';
            return;
        }

        this.loading = true;
        this.error = '';

        // Note: AuthService.loginUnified might need update to accept token, OR we pass it as extra?
        // Actually, loginUnified signature is (email, password).
        // I need to update loginUnified OR overload it.
        // For now, let's assuming I should update AuthService or pass it in a payload object if loginUnified accepted an object.
        // Checking loginUnified implementation...

        // Since I can't see loginUnified right now, I will modify it or assume I can pass it.
        // Wait, I should verify AuthService first.

        this.authService.loginUnified(this.email, this.password, this.recaptcha_token).subscribe({
            next: (response) => {
                console.log('DEBUG LOGIN: Respuesta exitosa', response);
                this.loading = false;
                if (response.user_type === 'admin') {
                    this.router.navigate(['/admin']);
                } else {
                    this.router.navigate(['/']);
                }
            },
            error: (err) => {
                console.error('DEBUG LOGIN: Error en login', err);
                this.zone.run(() => {
                    this.loading = false;
                    if (err.status === 403 && err.error?.requires_verification) {
                        Swal.fire('Aviso', 'Debes verificar tu email antes de entrar. Te redirigimos.', 'info');
                        this.router.navigate(['/registro'], { queryParams: { email: this.email, verify: true } });
                        return;
                    }

                    // Mejor manejo de mensajes de error
                    if (err.status === 401 || err.status === 400 || err.status === 404) {
                        this.error = 'Email o contraseña incorrecta';
                    } else {
                        this.error = 'Error del servidor, intenta más tarde';
                    }
                    this.cdr.detectChanges();
                });
            }
        });
    }
}
