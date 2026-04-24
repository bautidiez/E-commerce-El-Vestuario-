import { Injectable, inject } from '@angular/core';
import { Auth, GoogleAuthProvider, signInWithPopup, UserCredential } from '@angular/fire/auth';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';
import { from, Observable, tap, catchError, throwError } from 'rxjs';
import Swal from 'sweetalert2';

@Injectable({
  providedIn: 'root'
})
export class GoogleAuthService {
  private auth = inject(Auth);
  private http = inject(HttpClient);
  private router = inject(Router);
  private apiUrl = environment.apiUrl;

  async loginWithGoogle(): Promise<void> {
    const provider = new GoogleAuthProvider();
    provider.setCustomParameters({
      prompt: 'select_account'
    });

    try {
      const result: UserCredential = await signInWithPopup(this.auth, provider);
      const idToken = await result.user.getIdToken();
      
      // Enviar el token a nuestro backend
      this.http.post<any>(`${this.apiUrl}/auth/google`, { idToken }).pipe(
        tap(res => {
          if (res.access_token) {
            localStorage.setItem('token', res.access_token);
            localStorage.setItem('user_type', 'cliente');
            localStorage.setItem('cliente', JSON.stringify(res.cliente));
            
            Swal.fire({
              icon: 'success',
              title: '¡Bienvenido!',
              text: `Hola ${res.cliente.nombre}`,
              timer: 2000,
              showConfirmButton: false
            });
            
            this.router.navigate(['/']);
          }
        }),
        catchError(err => {
          console.error('Error enviando token al backend:', err);
          Swal.fire('Error', 'Hubo un problema al iniciar sesión con Google', 'error');
          return throwError(() => err);
        })
      ).subscribe();

    } catch (error: any) {
      console.error('Error Google Popup:', error);
      if (error.code !== 'auth/popup-closed-by-user') {
        Swal.fire('Error', 'No se pudo abrir la ventana de Google', 'error');
      }
    }
  }

  logout(): void {
    this.auth.signOut();
    localStorage.removeItem('token');
    localStorage.removeItem('user_type');
    localStorage.removeItem('cliente');
    this.router.navigate(['/login']);
  }
}
