import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';

@Component({
    selector: 'app-order-success',
    standalone: true,
    imports: [CommonModule, RouterModule],
    templateUrl: './order-success.html',
    styleUrl: './order-success.css'
})
export class OrderSuccessComponent implements OnInit {
    order: any = null;

    constructor(private router: Router) {
        const nav = this.router.getCurrentNavigation();
        if (nav?.extras?.state?.['order']) {
            this.order = nav.extras.state['order'];
        }
    }

    ngOnInit() {
        if (!this.order && history.state.order) {
            this.order = history.state.order;
        }

        if (this.order) {
            console.log('Order Success loaded:', this.order);
            // Ensure method keys are preserved
            if (!this.order.metodo_pago_frontend_key && this.order.metodo_pago) {
                this.order.metodo_pago_frontend_key = this.order.metodo_pago;
            }
        }
    }

    checkPayment(key: string): boolean {
        if (!this.order) return false;

        const setKey = this.order.metodo_pago_frontend_key || this.order.metodo_pago;

        // Match key directly
        if (setKey === key) return true;

        // CRITICAL: If we have a specific frontend key, rely ONLY on it.
        // Don't fall back to legacy name matching which might be ambiguous (e.g. backend naming "Efectivo Local" as "Transferencia")
        if (this.order.metodo_pago_frontend_key) return false;

        // Legacy name matching fallback
        const name = (this.order.metodo_pago_nombre || '').toLowerCase();
        if (key === 'efectivo_local') return name.includes('local') || name.includes('retiro');
        if (key === 'transferencia') return name.includes('transferencia') && !name.includes('local');
        if (key === 'efectivo') return (name.includes('efectivo') || name.includes('rapipago')) && !name.includes('local');
        if (key === 'mercadopago') return name.includes('mercado') || name.includes('tarjeta');

        return false;
    }

    getWhatsAppUrl(numberIndex: 1 | 2 = 1): string {
        if (!this.order) return '';
        const phoneNumber = '5493584171716';

        let msg = `Hola! Hice el pedido #${this.order.numero_pedido}. Adjunto comprobante. Total: $${this.order.total}`;

        if (this.checkPayment('efectivo_local')) {
            const itemsList = this.order.items?.map((i: any) => `- ${i.producto_nombre || i.producto?.nombre} x${i.cantidad}`).join('\n') || '';
            msg = `*NUEVO PEDIDO #${this.order.numero_pedido}*\n\n*Detalle:*\n${itemsList}\n\n*Pago:* Efectivo en local\n*Total:* $${this.order.total}\n\nHola! Confirmo mi pedido.`;
        } else if (this.checkPayment('transferencia')) {
            msg = `Hola! Hice el pedido #${this.order.numero_pedido} via Transferencia.\nAdjunto comprobante.\n*Total:* $${this.order.total}`;
        }

        return `https://wa.me/${phoneNumber}?text=${encodeURIComponent(msg)}`;
    }
}
