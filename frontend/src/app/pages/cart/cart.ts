import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { CartService } from '../../services/cart.service';
import { CartItem } from '../../models/interfaces';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { Router } from '@angular/router';
import { ShippingCalculatorComponent } from '../../components/shipping-calculator/shipping-calculator';

@Component({
  selector: 'app-cart',
  standalone: true,
  imports: [CommonModule, RouterModule, ShippingCalculatorComponent],
  templateUrl: './cart.html',
  styleUrl: './cart.css'
})
export class CartComponent implements OnInit {
  items: CartItem[] = [];
  total = 0;
  showLoginError = false;

  constructor(
    private cartService: CartService,
    private apiService: ApiService,
    private authService: AuthService,
    private router: Router
  ) { }

  ngOnInit() {
    this.cartService.cart$.subscribe(items => {
      this.items = items;
      this.total = this.cartService.getTotal();
    });
  }

  removeItem(index: number) {
    this.cartService.removeItem(index);
  }

  updateQuantity(index: number, cantidad: number) {
    if (cantidad > 0) {
      this.cartService.updateQuantity(index, cantidad);
    }
  }

  getSubtotal(): number {
    return this.items.reduce((sum, item) => {
      return sum + (item.precio_unitario * item.cantidad);
    }, 0);
  }

  continuarCompra() {
    if (this.authService.isLoggedIn()) {
      this.router.navigate(['/checkout']);
    } else {
      this.showLoginError = true;
      // Scrollear al mensaje
      setTimeout(() => {
        const element = document.getElementById('login-required-msg');
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 100);
    }
  }

  getDescuentoTotal(): number {
    return this.items.reduce((sum, item) => {
      return sum + (item.descuento || 0);
    }, 0);
  }

  getFormattedImageUrl(url: string | null | undefined): string {
    return this.apiService.getFormattedImageUrl(url);
  }

  getPrecioConTransferencia(): number {
    // 15% descuento por transferencia/efectivo
    return this.total * 0.85;
  }
}
