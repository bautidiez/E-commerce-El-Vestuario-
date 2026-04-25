import { Component, ChangeDetectorRef, OnInit } from '@angular/core';
import { RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../services/api.service';
import { ToastService } from '../../../services/toast.service';
import { QuillModule } from 'ngx-quill';

@Component({
    selector: 'app-newsletter-admin',
    standalone: true,
    imports: [CommonModule, FormsModule, QuillModule, RouterModule],
    templateUrl: './newsletter-admin.html',
    styleUrl: './newsletter-admin.css'
})
export class NewsletterAdminComponent implements OnInit {
    subject: string = '';
    content: string = '';
    testEmail: string = '';

    // Programación
    tipoProgramacion: string = 'inmediato'; // 'inmediato', 'unica', 'semanal', 'mensual'
    fechaUnica: string = '';
    diaSemana: number = 0; // 0=Lunes
    posicionMes: number = 1; // 1=Primero, 5=Último
    horaEnvio: string = '10:00';

    isLoading: boolean = false;
    history: any[] = [];
    scheduled: any[] = [];
    lastStats: any = null;
    totalSubscribers: number = 0;

    diasSemana = [
        { id: 0, nombre: 'Lunes' },
        { id: 1, nombre: 'Martes' },
        { id: 2, nombre: 'Miércoles' },
        { id: 3, nombre: 'Jueves' },
        { id: 4, nombre: 'Viernes' },
        { id: 5, nombre: 'Sábado' },
        { id: 6, nombre: 'Domingo' }
    ];

    posicionesMes = [
        { id: 1, nombre: 'Primer' },
        { id: 2, nombre: 'Segundo' },
        { id: 3, nombre: 'Tercer' },
        { id: 4, nombre: 'Cuarto' },
        { id: 5, nombre: 'Último' }
    ];

    constructor(
        private apiService: ApiService,
        private toastService: ToastService,
        private cdr: ChangeDetectorRef
    ) { }

    ngOnInit() {
        this.loadHistory();
        this.loadScheduled();
        this.loadStats();
    }

    loadHistory() {
        this.apiService.getNewsletterHistory().subscribe({
            next: (history) => {
                this.history = history;
                this.cdr.detectChanges();
            }
        });
    }

    loadScheduled() {
        this.apiService.getScheduledNewsletters().subscribe({
            next: (res) => {
                this.scheduled = res;
                this.cdr.detectChanges();
            }
        });
    }

    loadStats() {
        this.apiService.getNewsletterStats().subscribe({
            next: (res) => {
                this.totalSubscribers = res.total_subscribers;
                this.cdr.detectChanges();
            }
        });
    }

    send(isTest: boolean = true) {
        if (!this.subject || !this.content) {
            this.toastService.show('Asunto y Mensaje son requeridos', 'error');
            return;
        }

        if (isTest) {
            if (!this.testEmail) {
                this.toastService.show('Ingresá un email para probar', 'error');
                return;
            }
            this.sendTest();
        } else {
            if (this.tipoProgramacion === 'inmediato') {
                this.sendNow();
            } else {
                this.scheduleEmail();
            }
        }
    }

    private sendTest() {
        this.isLoading = true;
        this.cdr.detectChanges();

        this.apiService.sendNewsletter({
            subject: this.subject,
            content: this.content,
            test_email: this.testEmail
        }).subscribe({
            next: (res: any) => {
                this.isLoading = false;
                this.toastService.show('Email de prueba enviado', 'success');
                this.cdr.detectChanges();
            },
            error: (err) => {
                this.isLoading = false;
                this.toastService.show('Error al enviar prueba', 'error');
                this.cdr.detectChanges();
            }
        });
    }

    private sendNow() {
        if (!confirm('¿Estás seguro de enviar este newsletter a TODOS los suscriptores? Esta acción no se puede deshacer.')) {
            return;
        }

        this.isLoading = true;
        this.lastStats = null;
        this.cdr.detectChanges();

        this.apiService.sendNewsletter({
            subject: this.subject,
            content: this.content
        }).subscribe({
            next: (res: any) => {
                this.isLoading = false;
                this.lastStats = res;
                this.toastService.show(res.message, 'success');
                this.loadHistory();
                this.cdr.detectChanges();
            },
            error: (err) => {
                this.isLoading = false;
                const msg = err.error?.error || 'Error al enviar newsletter';
                this.toastService.show(msg, 'error');
                this.cdr.detectChanges();
            }
        });
    }

    private scheduleEmail() {
        if (this.tipoProgramacion === 'unica' && !this.fechaUnica) {
            this.toastService.show('Elegí una fecha para programar', 'error');
            return;
        }

        this.isLoading = true;
        this.cdr.detectChanges();

        const payload = {
            subject: this.subject,
            content: this.content,
            tipo: this.tipoProgramacion,
            scheduled_at: this.tipoProgramacion === 'unica' ? this.fechaUnica : null,
            dia_semana: (this.tipoProgramacion === 'semanal' || this.tipoProgramacion === 'mensual') ? this.diaSemana : null,
            posicion_mes: this.tipoProgramacion === 'mensual' ? this.posicionMes : null,
            hora_envio: this.horaEnvio
        };

        this.apiService.scheduleNewsletter(payload).subscribe({
            next: (res) => {
                this.isLoading = false;
                this.toastService.show('Email programado con éxito', 'success');
                this.loadScheduled();
                this.resetForm();
                this.cdr.detectChanges();
            },
            error: (err) => {
                this.isLoading = false;
                this.toastService.show('Error al programar', 'error');
                this.cdr.detectChanges();
            }
        });
    }

    deleteScheduled(id: number) {
        if (!confirm('¿Deseas eliminar esta programación?')) return;

        this.apiService.deleteScheduledNewsletter(id).subscribe({
            next: () => {
                this.toastService.show('Programación eliminada', 'success');
                this.loadScheduled();
            }
        });
    }

    resetForm() {
        this.subject = '';
        this.content = '';
        this.tipoProgramacion = 'inmediato';
    }

    copyFromHistory(item: any) {
        this.subject = item.asunto;
        this.content = item.contenido;
        this.toastService.show('Contenido copiado al editor', 'info');
        window.scrollTo({ top: 0, behavior: 'smooth' });
        this.cdr.detectChanges();
    }

    getDiaNombre(id: number): string {
        return this.diasSemana.find(d => d.id === id)?.nombre || '';
    }

    getPosicionNombre(id: number): string {
        return this.posicionesMes.find(p => p.id === id)?.nombre || '';
    }
}
