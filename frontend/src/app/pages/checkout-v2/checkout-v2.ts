import { Component, OnInit, ChangeDetectorRef, NgZone, ApplicationRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CartItem, EnvioOption, Promocion, CONFIG } from '../../models/interfaces';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { CartService } from '../../services/cart.service';
import { CheckoutService } from '../../services/checkout.service';
import { ApiService } from '../../services/api.service';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
    selector: 'app-checkout-v2',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, FormsModule, RouterModule],
    templateUrl: './checkout-v2.html',
    styleUrl: './checkout-v2.css'
})
export class CheckoutV2Component implements OnInit {
    currentStep = 1;
    items: CartItem[] = [];
    total = 0;

    // Forms
    datosForm: FormGroup;
    envioForm: FormGroup;
    pagoForm: FormGroup;
    couponForm: FormGroup;

    // Data from backend
    shippingOptions: EnvioOption[] = [];
    transferData: any = null;
    loading = false;
    orderCreated: any = null;
    appliedCoupon: Promocion | null = null;
    couponError: string = '';
    couponSuccess: string = '';
    validatingCoupon = false;

    // Category mapping for logic
    categoriesMap = new Map<number, any>();

    constructor(
        private fb: FormBuilder,
        private cartService: CartService,
        private checkoutService: CheckoutService,
        private apiService: ApiService,
        private authService: AuthService,
        private router: Router,
        private cdr: ChangeDetectorRef,
        private zone: NgZone,
        private appRef: ApplicationRef
    ) {
        this.datosForm = this.fb.group({
            email: ['', [Validators.required, Validators.email]],
            codigo_postal: ['', [Validators.required, Validators.minLength(4), Validators.pattern('^[0-9]*$')]],
            nombre: ['', [Validators.required, Validators.minLength(2)]],
            apellido: ['', [Validators.required, Validators.minLength(2)]],
            telefono: ['', [Validators.required]],
            calle: ['', [Validators.required]],
            altura: ['', [Validators.required]],
            piso: [''],
            depto: [''],
            ciudad: ['', [Validators.required]],
            // provincia: Eliminado duplicado si existía
            provincia: ['', [Validators.required]],
            dni: ['', [Validators.required, Validators.minLength(7)]],
            observaciones: ['']
        });

        this.envioForm = this.fb.group({
            metodo_id: ['', Validators.required],
            sucursal_info: [''] // New field for branch details
        });

        this.pagoForm = this.fb.group({
            metodo: ['', Validators.required],
            // Card data (simulated for UI)
            card_number: [''],
            card_name: [''],
            card_expiry: [''],
            card_cvv: [''],
            card_dni: ['']
        });

        this.couponForm = this.fb.group({
            code: ['', Validators.required]
        });
    }

    ngOnInit() {
        console.log('DEBUG: CHECKOUT V2 LOADED');
        this.cartService.cart$.subscribe(items => {
            this.items = items;
            this.total = this.cartService.getTotal();
            if (this.items.length === 0 && !this.orderCreated) {
                this.router.navigate(['/carrito']);
            }
        });

        this.checkoutService.getDatosTransferencia().subscribe(data => {
            this.transferData = data;
        });

        this.loadCategorias();
        this.prefillClientData();
        this.setupConditionalValidation();
    }

    loadCategorias() {
        this.apiService.getCategorias().subscribe({
            next: (data) => {
                this.buildCategoriesMap(data);
                this.cdr.detectChanges(); // Refresh UI once categories loaded
            }
        });
    }

    buildCategoriesMap(nodes: any[]) {
        nodes.forEach(node => {
            this.categoriesMap.set(node.id, node);
            if (node.subcategorias && node.subcategorias.length > 0) {
                this.buildCategoriesMap(node.subcategorias);
            }
        });
    }

    checkIfShort(categoriaId: number): boolean {
        // Fallback for direct ID match (Shorts usually ID 8 or 2) even if map not loaded yet
        if (CONFIG.CATEGORIAS.IDS_SHORTS.includes(+categoriaId)) return true;

        if (this.categoriesMap.size === 0) return false;

        let currentId: number | null = +categoriaId;
        let attempts = 0;

        while (currentId !== null && attempts < 10) {
            if (CONFIG.CATEGORIAS.IDS_SHORTS.includes(currentId)) return true;

            const category = this.categoriesMap.get(currentId);
            if (category) {
                if (category.nombre && category.nombre.toLowerCase().trim().includes('short')) return true;

                if (category.categoria_padre_id) {
                    currentId = +category.categoria_padre_id;
                } else {
                    break;
                }
            } else {
                break;
            }
            attempts++;
        }
        return false;
    }

    prefillClientData() {
        const cliente = this.authService.getCliente();
        if (cliente) {
            this.datosForm.patchValue({
                email: cliente.email,
                nombre: cliente.nombre || '',
                apellido: cliente.apellido || '',
                telefono: cliente.telefono || '',
                codigo_postal: cliente.codigo_postal || '',
                calle: cliente.calle || '',
                altura: cliente.altura || '',
                piso: cliente.piso || '',
                depto: '',
                ciudad: cliente.ciudad || '',
                provincia: cliente.provincia || '',
                dni: cliente.dni || '',
                observaciones: ''
            });
        }
    }

    setupConditionalValidation() {
        this.envioForm.get('metodo_id')?.valueChanges.subscribe(id => {
            const isRetiro = this.isRetiro(id);
            const addressFields = ['calle', 'altura', 'ciudad', 'provincia'];

            addressFields.forEach(field => {
                const control = this.datosForm.get(field);
                if (isRetiro) {
                    control?.clearValidators();
                } else {
                    control?.setValidators([Validators.required]);
                }
                control?.updateValueAndValidity();
            });
        });
    }

    isRetiro(id?: string): boolean {
        const selectedId = id || this.envioForm.get('metodo_id')?.value;
        const options = this.getOpcionesRetiro();
        return options.some(opt => opt.id === selectedId);
    }

    getBaseTotal() {
        const shipping = this.getSelectedShipping();
        let shippingCost = shipping ? shipping.costo : 0;
        if (shipping && shipping.descuento) {
            shippingCost = 0;
        }
        return this.total + shippingCost;
    }

    getDiscountedHeaderPrice(metodo: string) {
        if (!['transferencia', 'efectivo', 'efectivo_local'].includes(metodo)) {
            return this.getBaseTotal();
        }

        const shipping = this.getSelectedShipping();
        let shippingCost = shipping ? shipping.costo : 0;
        if (shipping && shipping.descuento) {
            shippingCost = 0;
        }

        let itemsDiscountedTotal = 0;

        this.items.forEach(item => {
            const effectiveItemTotal = (item.precio_unitario * item.cantidad) - (item.descuento || 0);
            const esShort = this.checkIfShort(item.producto.categoria_id);
            const factor = esShort ? 0.90 : 0.85;

            itemsDiscountedTotal += effectiveItemTotal * factor;
        });

        return itemsDiscountedTotal + shippingCost;
    }

    nextStep() {
        if (this.currentStep === 2) {
            // Validate that shipping is selected
            if (this.envioForm.invalid) {
                this.envioForm.markAllAsTouched();
                alert('Por favor selecciona una forma de envío');
                return;
            }
            // Validate personal data
            if (this.datosForm.invalid) {
                this.datosForm.markAllAsTouched();
                // Scroll to first error?
                return;
            }
        }
        this.currentStep++;
        window.scrollTo(0, 0);
    }

    prevStep() {
        this.currentStep--;
        window.scrollTo(0, 0);
    }

    private isCalculatingShipping = false;

    calculateShipping() {
        console.log('=== DEBUG SHIPPING CALC START ===');
        console.log('DEBUG: Items BEFORE sync:', this.items);

        // CRITICAL: Always sync items from cart service first
        this.items = this.cartService.getCartItems();
        console.log('DEBUG: Items AFTER sync:', this.items);
        console.log('DEBUG: Items length:', this.items?.length || 0);
        console.log('DEBUG: Items JSON:', JSON.stringify(this.items));

        const cp = this.datosForm.get('codigo_postal')?.value;
        console.log('DEBUG: Codigo Postal:', cp);

        // Prevent re-calc if already calculating or invalid CP
        if (this.isCalculatingShipping || !cp || cp.length < 4) {
            console.log('DEBUG: Aborting - already calculating or invalid CP');
            return;
        }

        // Double check items are present
        if (!this.items || this.items.length === 0) {
            console.error('CRITICAL: No items in cart! Cannot calculate shipping.');
            console.error('Cart Service value:', this.cartService.getCartItems());
            return;
        }

        this.loading = true;
        this.isCalculatingShipping = true;

        console.log('DEBUG: Calling checkoutService.calcularEnvio with:', { cp, items: this.items });

        this.checkoutService.calcularEnvio(cp, this.items).subscribe({
            next: (options) => {
                this.zone.run(() => {
                    this.shippingOptions = options;
                    this.cdr.detectChanges();
                });
            },
            error: (err) => {
                this.zone.run(() => {
                    console.error('Error calculando envío', err);
                    this.shippingOptions = []; // Clear options on error
                });
            },
            complete: () => {
                this.zone.run(() => {
                    this.loading = false;
                    this.isCalculatingShipping = false;
                    this.cdr.detectChanges();
                });
            }
        });
    }

    getSelectedShipping() {
        const id = this.envioForm.get('metodo_id')?.value;
        return this.shippingOptions.find(o => o.id === id);
    }

    getOpcionesDomicilio() {
        return this.shippingOptions.filter(o => {
            const name = o.nombre.toLowerCase();
            const isHomeKeyword = name.includes('domicilio') || name.includes('estándar') || name.includes('envío');
            const isPickupKeyword = name.includes('sucursal') || name.includes('retiro') || name.includes('local');
            return isHomeKeyword && !isPickupKeyword;
        });
    }

    getOpcionesRetiro() {
        return this.shippingOptions.filter(o => {
            const name = o.nombre.toLowerCase();
            return name.includes('sucursal') || name.includes('retiro') || name.includes('local');
        });
    }

    isSucursalSelected(): boolean {
        const shipping = this.getSelectedShipping();
        if (!shipping) return false;
        const name = shipping.nombre.toLowerCase();
        // Exclude "Retiro en Local" (our local store) usually, but user asked for courier branches.
        // "Retiro en Local (Río Cuarto)" doesn't need external links, but maybe needs specifying who picks up?
        // User specifically asked for Andreani/Correo links.
        return name.includes('sucursal') && !name.includes('río cuarto');
    }

    isAndreaniSelected(): boolean {
        const shipping = this.getSelectedShipping();
        return shipping ? shipping.nombre.toLowerCase().includes('andreani') : false;
    }

    isCorreoArgentinoSelected(): boolean {
        const shipping = this.getSelectedShipping();
        return shipping ? shipping.nombre.toLowerCase().includes('correo') : false;
    }

    // Helper to get total of products BEFORE any discount
    getSubtotalBruto(): number {
        return this.items.reduce((sum, item) => {
            return sum + (item.precio_unitario * item.cantidad);
        }, 0);
    }

    // Helper to get total of product-specific discounts
    getDescuentoProductos(): number {
        return this.items.reduce((sum, item) => {
            return sum + (item.descuento || 0);
        }, 0);
    }

    getDiscountAmount() {
        const metodoPago = this.pagoForm.get('metodo')?.value;

        if (['efectivo_local', 'transferencia', 'efectivo'].includes(metodoPago)) {
            let totalDiscount = 0;
            this.items.forEach(item => {
                const esShort = this.checkIfShort(item.producto.categoria_id);
                // Discount applies on the 'Effective Total' of the item (after quantity/promo discounts)
                const effectiveItemTotal = (item.precio_unitario * item.cantidad) - (item.descuento || 0);

                const porcentaje = esShort ? 0.10 : 0.15;
                totalDiscount += effectiveItemTotal * porcentaje;
            });
            return totalDiscount;
        }
        return 0;
    }

    getFinalTotal() {
        const shipping = this.getSelectedShipping();
        const metodoPago = this.pagoForm.get('metodo')?.value;

        // PASO 1: Calcular total de productos
        let productsTotal = this.total;

        // Si es efectivo/transferencia, recalculamos con descuento mixto (10% shorts, 15% resto)
        if (['efectivo_local', 'transferencia', 'efectivo'].includes(metodoPago)) {
            productsTotal = 0;
            this.items.forEach(item => {
                // Effective Price being paid for this item in the cart
                const effectiveItemTotal = (item.precio_unitario * item.cantidad) - (item.descuento || 0);

                const esShort = this.checkIfShort(item.producto.categoria_id);
                const factor = esShort ? 0.90 : 0.85;

                productsTotal += effectiveItemTotal * factor;
            });
        }

        // PASO 2: Calcular costo de envío
        let shippingCost = shipping ? shipping.costo : 0;
        if (shipping && shipping.descuento) {
            shippingCost = 0; // Free shipping
        }

        // PASO 3: Aplicar cupón si existe (solo si NO se aplicó descuento de transferencia/efectivo)
        if (this.appliedCoupon && !['efectivo_local', 'transferencia', 'efectivo'].includes(metodoPago)) {
            if (this.appliedCoupon.envio_gratis) {
                if (shipping && !shipping.descuento) {
                    shippingCost = 0;
                }
            } else if (this.appliedCoupon.tipo_promocion_nombre === 'descuento_porcentaje') {
                productsTotal -= (this.total * this.appliedCoupon.valor / 100);
            } else if (this.appliedCoupon.tipo_promocion_nombre === 'descuento_fijo') {
                productsTotal -= this.appliedCoupon.valor;
            }
        }

        return Math.max(0, productsTotal + shippingCost);
    }

    validateCoupon() {
        if (this.couponForm.invalid) return;

        const code = this.couponForm.get('code')?.value;
        this.validatingCoupon = true;
        this.couponError = '';
        this.couponSuccess = '';

        this.checkoutService.validarCupon(code).subscribe({
            next: (cupon) => {
                this.appliedCoupon = cupon;
                this.couponSuccess = `¡Cupón ${code} aplicado exitosamente!`;
                this.validatingCoupon = false;
                this.couponForm.reset();
                this.cdr.detectChanges();
            },
            error: (err) => {
                this.couponError = err.error?.error || 'Error al validar el cupón';
                this.validatingCoupon = false;
                this.appliedCoupon = null;
                this.cdr.detectChanges();
            }
        });
    }

    finalizarCompra() {
        if (this.datosForm.invalid || this.pagoForm.invalid) {
            this.datosForm.markAllAsTouched();
            this.pagoForm.markAllAsTouched();
            return;
        }

        const shipping = this.getSelectedShipping();
        const datos = this.datosForm.value;

        // Calculate FINAL shipping cost (after free shipping discount)
        let finalShippingCost = shipping ? shipping.costo : 0;
        if (shipping && shipping.descuento) {
            finalShippingCost = 0; // Free shipping applied
        }

        const pedidoData = {
            cliente_nombre: `${datos.nombre} ${datos.apellido}`, // Concatenate for backend compatibility
            cliente_email: datos.email,
            cliente_telefono: datos.telefono,
            calle: datos.calle,
            altura: datos.altura,
            piso: datos.piso,
            depto: datos.depto,
            ciudad: datos.ciudad,
            provincia: datos.provincia,
            codigo_postal: datos.codigo_postal,
            dni: datos.dni,
            observaciones: datos.observaciones + (this.envioForm.get('sucursal_info')?.value ? `\n\n[Sucursal: ${this.envioForm.get('sucursal_info')?.value}]` : ''),

            metodo_envio: shipping?.nombre,
            costo_envio: finalShippingCost, // FIXED: Send FINAL cost (0 if free shipping)
            metodo_pago: this.pagoForm.get('metodo')?.value,

            items: this.items.map(i => ({
                producto_id: i.producto.id,
                talle_id: i.talle.id,
                cantidad: i.cantidad,
                precio_unitario: i.precio_unitario
            })),
            subtotal: this.total,
            total: this.getFinalTotal()
        };

        this.loading = true;
        this.checkoutService.crearPedido(pedidoData).subscribe({
            next: (order) => {
                this.zone.run(() => {
                    this.loading = false;
                    this.orderCreated = order;
                    
                    // Limpiar el carrito tras compra exitosa
                    this.cartService.clearCart();

                    // CRITICAL FIX: Override payment method string with what user actually selected
                    // This ensures UI shows the correct flow even if backend maps it to default ID 1 (Transferencia)
                    const selectedMethod = this.pagoForm.get('metodo')?.value;
                    if (selectedMethod) {
                        console.log('Frontend Payment Override:', selectedMethod);
                        this.orderCreated.metodo_pago_frontend_key = selectedMethod;
                    }

                    // Redirect to dedicated Success Page
                    console.log('DEBUG CHECKOUT V2: Order Created, redirecting to success page.', this.orderCreated);
                    this.router.navigate(['/pedido-exitoso'], { state: { order: this.orderCreated } });

                    // Auto-open MP link if card payment (keep this logic if needed, or rely on success page)
                    if (pedidoData.metodo_pago === 'mercadopago_card') {
                        const mpLink = 'https://link.mercadopago.com.ar/elvestuarior4';
                        window.open(mpLink, '_blank');
                    }
                });
            },
            error: (err) => {
                this.zone.run(() => {
                    console.error("Error creating order:", err);
                    const msg = err.error?.error || err.message || "Error desconocido al procesar el pedido";
                    alert("Error al crear el pedido: " + msg);
                    this.loading = false;
                    this.cdr.detectChanges();
                });
            }
        });
    }

    getFormattedImageUrl(url: string | null | undefined): string {
        return this.apiService.getFormattedImageUrl(url);
    }

    updateDiscount() {
        const selected = this.pagoForm.get('metodo')?.value;
        console.log('Payment method changed:', selected);
        if (selected) {
            localStorage.setItem('checkout_last_payment_method', selected);
        }
        this.cdr.detectChanges();
    }

    isPaymentMethod(order: any, methodKey: string): boolean {
        // 1. Check Frontend Override (Memory)
        if (order && order.metodo_pago_frontend_key) {
            return order.metodo_pago_frontend_key === methodKey;
        }

        // 2. Check LocalStorage Overlay (Most robust across reloads/mismatches)
        const storedMethod = localStorage.getItem('checkout_last_payment_method');
        // Only verify against stored method if we are in the success step to avoid false positives elsewhere
        if (this.currentStep === 4 && storedMethod) {
            return storedMethod === methodKey;
        }

        if (!order) return false;

        // 3. Fallback to Backend Name (Legacy)
        if (order.metodo_pago_nombre) {
            const name = order.metodo_pago_nombre.toLowerCase();
            switch (methodKey) {
                case 'efectivo_local':
                    return name.includes('local') || name.includes('retiro');
                case 'transferencia':
                    return name.includes('transferencia');
                case 'efectivo':
                    return (name.includes('efectivo') || name.includes('rapipago') || name.includes('facil')) && !name.includes('local');
                case 'mercadopago':
                    return name.includes('mercado') || name.includes('mp') || name.includes('tarjeta');
            }
        }

        return false;
    }

    getWhatsAppUrl(order: any, numberIndex: 1 | 2 = 1): string {
        if (!order) return '';
        const phoneNumber = '5493584171716';
        let msg = '';

        if (this.isPaymentMethod(order, 'efectivo_local')) {
            // 1. Efectivo en el local
            // Requisito: Detalle de la compra, Medio de pago: Efectivo en el local, Modo de envío, Total a pagar
            const itemsList = order.items?.map((i: any) => `- ${i.producto_nombre} (${i.talle_nombre}) x${i.cantidad}`).join('\n') || '';
            const envioMethod = order.envio?.transportista || 'Retiro en Local';

            msg = `*NUEVO PEDIDO #${order.numero_pedido}*\n\n*Detalle de la compra:*\n${itemsList}\n\n*Medio de pago:* Efectivo en el local\n*Modo de envío:* ${envioMethod}\n*Total a pagar:* $${order.total}\n\nHola! Quiero confirmar mi pedido.`;

        } else if (this.isPaymentMethod(order, 'mercadopago')) {
            // 2. Tarjeta / MP
            // Requisito: "Una vez realizado el pago, enviá el comprobante..." context
            msg = `Hola! Hice el pedido #${order.numero_pedido} pagando con Tarjeta/Mercado Pago.\nAdjunto el comprobante de pago para confirmar la compra.\n*Total:* $${order.total}`;

        } else if (this.isPaymentMethod(order, 'transferencia')) {
            // 3. Transferencia
            msg = `Hola! Hice el pedido #${order.numero_pedido} via Transferencia.\nAdjunto el comprobante de pago.\n*Total:* $${order.total}`;

        } else if (this.isPaymentMethod(order, 'efectivo')) {
            // 4. Rapipago/Pago Facil
            msg = `Hola! Hice el pedido #${order.numero_pedido} y ya realicé el pago en Rapipago/Pago Fácil.\nAdjunto el comprobante.\n*Total:* $${order.total}`;

        } else {
            msg = `Hola! Hice el pedido #${order.numero_pedido}. Adjunto comprobante. Total: $${order.total}`;
        }

        return `https://wa.me/${phoneNumber}?text=${encodeURIComponent(msg)}`;
    }
}
