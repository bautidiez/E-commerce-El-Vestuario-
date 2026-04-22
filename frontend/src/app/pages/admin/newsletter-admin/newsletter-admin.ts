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

    isLoading: boolean = false;
    history: any[] = [];
    lastStats: any = null;

    constructor(
        private apiService: ApiService,
        private toastService: ToastService,
        private cdr: ChangeDetectorRef
    ) { }

    ngOnInit() {
        this.loadHistory();
    }

    loadHistory() {
        this.apiService.getNewsletterHistory().subscribe({
            next: (history) => {
                this.history = history;
                this.cdr.detectChanges();
            }
        });
    }

    send(isTest: boolean = true) {
        if (!this.subject || !this.content) {
            this.toastService.show('Asunto y Mensaje son requeridos', 'error');
            return;
        }

        if (isTest && !this.testEmail) {
            this.toastService.show('Ingresá un email para probar', 'error');
            return;
        }

        if (!isTest && !confirm('¿Estás seguro de enviar este newsletter a TODOS los suscriptores? Esta acción no se puede deshacer.')) {
            return;
        }

        this.isLoading = true;
        this.lastStats = null;
        this.cdr.detectChanges();

        const payload = {
            subject: this.subject,
            content: this.content,
            test_email: isTest ? this.testEmail : null
        };

        this.apiService.sendNewsletter(payload).subscribe({
            next: (res: any) => {
                this.isLoading = false;
                this.lastStats = res;
                this.toastService.show(res.message, 'success');
                if (!isTest) {
                    this.loadHistory();
                }
                this.cdr.detectChanges();
            },
            error: (err) => {
                this.isLoading = false;
                console.error('Error enviando newsletter:', err);
                const msg = err.error?.error || 'Error al enviar newsletter';
                this.toastService.show(msg, 'error');
                this.cdr.detectChanges();
            }
        });
    }

    copyFromHistory(item: any) {
        this.subject = item.asunto;
        this.content = item.contenido;
        this.toastService.show('Contenido copiado al editor', 'info');
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
        this.cdr.detectChanges();
    }
}
