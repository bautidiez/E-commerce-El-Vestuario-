import { Directive, ElementRef, Input, OnInit } from '@angular/core';

@Directive({
  selector: 'img[appLazy]',
  standalone: true
})
export class LazyLoadDirective implements OnInit {
  @Input() appLazy: string = '';

  constructor(private el: ElementRef) {}

  ngOnInit() {
    // Si no hay IntersectionObserver (navegadores muy viejos), cargar de inmediato
    if (!('IntersectionObserver' in window)) {
      this.loadImage();
      return;
    }

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        this.loadImage();
        observer.unobserve(this.el.nativeElement);
      }
    }, {
      rootMargin: '50px' // Empezar a cargar 50px antes de que sea visible
    });

    observer.observe(this.el.nativeElement);
  }

  private loadImage() {
    if (this.appLazy) {
      // Si la URL es de Cloudinary, podemos agregar parámetros de optimización aquí si no vienen
      let finalUrl = this.appLazy;
      
      // Ejemplo de optimización automática si es URL de Cloudinary:
      // if (finalUrl.includes('cloudinary.com')) { ... }
      
      this.el.nativeElement.src = finalUrl;
    }
  }
}
