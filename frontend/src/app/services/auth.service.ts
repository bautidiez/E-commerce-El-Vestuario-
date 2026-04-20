import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { ApiService } from './api.service';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import Swal from 'sweetalert2';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private isAuthenticatedSubject = new BehaviorSubject<boolean>(this.isLoggedIn());
  public isAuthenticated$ = this.isAuthenticatedSubject.asObservable();
  private inactivityTimer: any = null;
  private readonly INACTIVITY_TIMEOUT = 8 * 60 * 60 * 1000; // 8 horas en milisegundos

  constructor(
    private apiService: ApiService,
    private router: Router
  ) {
    this.checkAuth();
    this.setupInactivityTimer();
  }

  login(username: string, password: string): Observable<any> {
    return this.apiService.login(username, password).pipe(
      tap((response) => {
        this.setSession(response, 'admin');
        this.resetInactivityTimer();
      })
    );
  }

  loginUnified(identifier: string, password: string, recaptcha_token?: string): Observable<any> {
    return this.apiService.loginUnified({ identifier, password, recaptcha_token }).pipe(
      tap((response) => {
        this.setSession(response, response.user_type);
        this.resetInactivityTimer();
      })
    );
  }

  loginCliente(email: string, password: string): Observable<any> {
    return new Observable(observer => {
      this.apiService.loginCliente({ email, password }).subscribe({
        next: (response) => {
          this.setSession(response, 'cliente');
          this.resetInactivityTimer();
          observer.next(response);
          observer.complete();
        },
        error: (error) => {
          observer.error(error);
        }
      });
    });
  }

  requestPasswordReset(email: string): Observable<any> {
    return this.apiService.post('/auth/forgot-password', { email });
  }

  setSession(response: any, type: 'admin' | 'cliente'): void {
    const tokenKey = type === 'admin' ? 'auth_token_admin' : 'auth_token_cliente';
    localStorage.setItem(tokenKey, response.access_token);
    
    // Mantener compatibilidad temporal con 'token' para componentes que aún lo usen directamente
    localStorage.setItem('token', response.access_token);
    localStorage.setItem('lastActivity', Date.now().toString());

    if (type === 'admin') {
      localStorage.setItem('admin', JSON.stringify(response.admin || response.cliente));
    } else {
      localStorage.setItem('cliente', JSON.stringify(response.cliente));
    }

    this.isAuthenticatedSubject.next(true);
  }

  updateCliente(cliente: any): void {
    localStorage.setItem('cliente', JSON.stringify(cliente));
  }

  resetPassword(token: string, password: string): Observable<any> {
    return this.apiService.post('/auth/reset-password', { token, password });
  }

  logout(): void {
    // Si queremos un logout total
    localStorage.removeItem('auth_token_admin');
    localStorage.removeItem('auth_token_cliente');
    localStorage.removeItem('token');
    localStorage.removeItem('admin');
    localStorage.removeItem('cliente');
    localStorage.removeItem('lastActivity');
    this.isAuthenticatedSubject.next(false);
    this.clearInactivityTimer();
    this.router.navigate(['/']);
  }

  logoutAdmin(): void {
    localStorage.removeItem('auth_token_admin');
    localStorage.removeItem('admin');
    if (!localStorage.getItem('auth_token_cliente')) {
      localStorage.removeItem('token');
      localStorage.removeItem('lastActivity');
      this.isAuthenticatedSubject.next(false);
    }
  }

  logoutCliente(): void {
    localStorage.removeItem('auth_token_cliente');
    localStorage.removeItem('cliente');
    if (!localStorage.getItem('auth_token_admin')) {
      localStorage.removeItem('token');
      localStorage.removeItem('lastActivity');
      this.isAuthenticatedSubject.next(false);
    }
  }

  isLoggedIn(): boolean {
    return !!localStorage.getItem('token');
  }

  getToken(type?: 'admin' | 'cliente'): string | null {
    if (type === 'admin') return localStorage.getItem('auth_token_admin');
    if (type === 'cliente') return localStorage.getItem('auth_token_cliente');
    return localStorage.getItem('token');
  }

  getAdmin(): any {
    const admin = localStorage.getItem('admin');
    return admin ? JSON.parse(admin) : null;
  }

  getCliente(): any {
    const cliente = localStorage.getItem('cliente');
    return cliente ? JSON.parse(cliente) : null;
  }

  private checkAuth(): void {
    if (this.isLoggedIn()) {
      // Verificar inactividad
      const lastActivity = localStorage.getItem('lastActivity');
      if (lastActivity) {
        const timeSinceActivity = Date.now() - parseInt(lastActivity);
        if (timeSinceActivity > this.INACTIVITY_TIMEOUT) {
          this.logout();
          return;
        }
      }

      const isAdmin = !!localStorage.getItem('admin');
      const isCliente = !!localStorage.getItem('cliente');

      if (isAdmin) {
        this.apiService.verifyToken().subscribe({
          next: () => {
            this.isAuthenticatedSubject.next(true);
            this.resetInactivityTimer();
          },
          error: (error) => {
            console.error('Verify Token Error:', error);
            if (error.status === 401 || error.status === 403) {
              this.logout();
            }
          }
        });
      } else if (isCliente) {
        this.apiService.verifyTokenCliente().subscribe({
          next: (response) => {
            // Restore session data if missing or outdated
            if (response && response.cliente) {
              localStorage.setItem('cliente', JSON.stringify(response.cliente));
            }
            this.isAuthenticatedSubject.next(true);
            this.resetInactivityTimer();
          },
          error: (error) => {
            console.error('Verify Token Cliente Error:', error);
            if (error.status === 401 || error.status === 403) {
              this.logout();
            }
          }
        });
      } else {
        // Fallback: Token exists but no type stored. Assume Client and try to verify/restore.
        console.log('DEBUG AUTH: Token exists but no type. Attempting to restore client session.');
        this.apiService.verifyTokenCliente().subscribe({
          next: (response) => {
            if (response && response.cliente) {
              this.setSession(response, 'cliente');
              console.log('DEBUG AUTH: Client session restored.');
            }
            this.resetInactivityTimer();
          },
          error: (err) => {
            console.error('DEBUG AUTH: Failed to restore session. Logging out.', err);
            this.logout();
          }
        });
      }
    }
  }

  private setupInactivityTimer(): void {
    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
    events.forEach(event => {
      document.addEventListener(event, () => {
        if (this.isLoggedIn()) {
          localStorage.setItem('lastActivity', Date.now().toString());
          this.resetInactivityTimer();
        }
      }, true);
    });
  }

  private resetInactivityTimer(): void {
    this.clearInactivityTimer();
    if (this.isLoggedIn()) {
      this.inactivityTimer = setTimeout(() => {
        const lastActivity = localStorage.getItem('lastActivity');
        if (lastActivity) {
          const timeSinceActivity = Date.now() - parseInt(lastActivity);
          if (timeSinceActivity >= this.INACTIVITY_TIMEOUT) {
            Swal.fire({
              title: 'Sesión expirada',
              text: 'Tu sesión ha expirado por inactividad.',
              icon: 'info',
              confirmButtonText: 'Entendido'
            });
            this.logout();
          }
        }
      }, this.INACTIVITY_TIMEOUT);
    }
  }

  private clearInactivityTimer(): void {
    if (this.inactivityTimer) {
      clearTimeout(this.inactivityTimer);
      this.inactivityTimer = null;
    }
  }
}
