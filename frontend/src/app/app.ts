import { Component, OnInit } from '@angular/core';
import { Router, NavigationEnd, RouterOutlet } from '@angular/router';
import { CommonModule } from '@angular/common';
import { HeaderComponent } from './components/header/header';
import { FooterComponent } from './components/footer/footer';
import { WhatsAppButtonComponent } from './components/whatsapp-button/whatsapp-button';
import { ToastComponent } from './components/toast/toast';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, HeaderComponent, FooterComponent, WhatsAppButtonComponent, CommonModule, ToastComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit {
  title = 'El Vestuario';
  isAdminRoute = false;

  constructor(private router: Router) { }

  ngOnInit() {
    // Detectar si estamos en una ruta de admin
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe((event: NavigationEnd) => {
      this.isAdminRoute = event.url.startsWith('/admin');
      if (this.isAdminRoute) {
        document.body.classList.add('admin-body');
        document.body.classList.add('admin-layout');
        document.documentElement.classList.add('admin-layout');
      } else {
        document.body.classList.remove('admin-body');
        document.body.classList.remove('admin-layout');
        document.documentElement.classList.remove('admin-layout');
      }
      window.scrollTo(0, 0);
    });

    // Ocultar pantalla de carga después de 2 segundos
    setTimeout(() => {
      const loadingScreen = document.getElementById('loading-screen');
      if (loadingScreen) {
        loadingScreen.classList.add('fade-out');
        setTimeout(() => {
          loadingScreen.remove();
        }, 500);
      }
    }, 2000); // ← Cambiado de 2500 a 2000
  }
}
