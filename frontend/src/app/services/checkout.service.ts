import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { CartItem, EnvioOption } from '../models/interfaces';

@Injectable({
    providedIn: 'root'
})
export class CheckoutService {
    private apiUrl = environment.apiUrl;

    constructor(private http: HttpClient) { }

    private getHeaders() {
        const token = localStorage.getItem('token');
        return {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        };
    }

    // Cálculo de Envío
    calcularEnvio(codigo_postal: string, items: CartItem[] = []): Observable<EnvioOption[]> {
        return this.http.post<EnvioOption[]>(`${this.apiUrl}/envios/calcular`, { codigo_postal, items });
    }

    // Gestión de Pedidos
    crearPedido(datosPedido: any): Observable<any> {
        return this.http.post<any>(`${this.apiUrl}/orders`, datosPedido);
    }

    getPedido(id: number): Observable<any> {
        return this.http.get<any>(`${this.apiUrl}/orders/${id}`);
    }

    getPedidosCliente(email: string): Observable<any[]> {
        return this.http.get<any[]>(`${this.apiUrl}/orders/by-customer/${email}`);
    }

    // Pagos
    getDatosTransferencia(): Observable<any> {
        return this.http.get<any>(`${this.apiUrl}/payments/transfer-data`);
    }

    confirmarTransferencia(orderId: number): Observable<any> {
        return this.http.post<any>(`${this.apiUrl}/payments/confirm-transfer/${orderId}`, {});
    }

    validarCupon(codigo: string): Observable<any> {
        return this.http.post<any>(`${this.apiUrl}/promociones/validar`, { codigo });
    }

    // Gestión de Cuenta (Cliente)
    updateProfile(data: any): Observable<any> {
        return this.http.put<any>(`${this.apiUrl}/clientes/me`, data, this.getHeaders());
    }

    changePassword(data: any): Observable<any> {
        return this.http.post<any>(`${this.apiUrl}/clientes/change-password`, data, this.getHeaders());
    }

    getMyOrders(): Observable<any[]> {
        return this.http.get<any[]>(`${this.apiUrl}/clientes/me/orders`, this.getHeaders());
    }

    deleteOrder(id: number): Observable<any> {
        return this.http.delete<any>(`${this.apiUrl}/clientes/me/orders/${id}`, this.getHeaders());
    }
}
