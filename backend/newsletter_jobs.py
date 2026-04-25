from datetime import datetime, timedelta
from models import db, Cliente, ScheduledNewsletter, NewsletterHistory
from services.notification_service import NotificationService
import pytz

def process_scheduled_newsletters(app):
    """
    Tarea de fondo para procesar newsletters programados.
    Se ejecuta cada 1 minuto (o lo configurado).
    """
    with app.app_context():
        try:
            # Argentina Time (GMT-3)
            arg_tz = pytz.timezone('America/Argentina/Buenos_Aires')
            now_arg = datetime.now(arg_tz)
            now_utc = datetime.utcnow()
            
            # 1. Buscar newsletters activos
            scheduled = ScheduledNewsletter.query.filter_by(activa=True).all()
            
            for item in scheduled:
                should_send = False
                
                if item.tipo == 'unica':
                    # Comparar en UTC para precisión de base de datos
                    if item.scheduled_at and item.scheduled_at <= now_utc and not item.last_run_at:
                        should_send = True
                
                elif item.tipo == 'semanal':
                    # dia_semana: 0=Lunes, 6=Domingo
                    current_day = now_arg.weekday()
                    current_time = now_arg.strftime("%H:%M")
                    
                    if current_day == item.dia_semana and current_time == item.hora_envio:
                        # Evitar doble envío en el mismo día
                        if not item.last_run_at or item.last_run_at.date() < now_utc.date():
                            should_send = True
                
                elif item.tipo == 'mensual':
                    # Posición del mes (1=primero, 5=último) y día de la semana
                    current_day = now_arg.weekday()
                    current_time = now_arg.strftime("%H:%M")
                    
                    if current_day == item.dia_semana and current_time == item.hora_envio:
                        # Calcular posición actual
                        pos = (now_arg.day - 1) // 7 + 1
                        
                        # Manejo especial para "último" (pos=5)
                        es_ultimo = False
                        if item.posicion_mes == 5:
                            # Si sumamos 7 días y cambia el mes, es el último
                            proxima_semana = now_arg + timedelta(days=7)
                            if proxima_semana.month != now_arg.month:
                                es_ultimo = True
                        
                        if pos == item.posicion_mes or (item.posicion_mes == 5 and es_ultimo):
                            if not item.last_run_at or item.last_run_at.date() < now_utc.date():
                                should_send = True
                
                if should_send:
                    print(f"DEBUG SCHEDULER: Ejecutando newsletter programado ID {item.id} - {item.asunto}")
                    
                    # Obtener destinatarios
                    recipients = []
                    if item.destinatarios:
                        import json
                        try:
                            # Formato: [{"email": "...", "nombre": "..."}, ...]
                            recipients = json.loads(item.destinatarios)
                        except:
                            print(f"ERROR: No se pudo parsear destinatarios del programado {item.id}")
                    
                    if not recipients:
                        clientes = Cliente.query.filter_by(acepta_newsletter=True).all()
                        recipients = [{'email': c.email, 'nombre': c.nombre} for c in clientes]
                    
                    if recipients:
                        sent_count = NotificationService.send_newsletter(item.asunto, item.contenido, recipients)
                        
                        # Registrar en historial
                        hist = NewsletterHistory(
                            asunto=item.asunto,
                            contenido=item.contenido,
                            sent_count=sent_count
                        )
                        db.session.add(hist)
                    
                    # Actualizar estado del programado
                    item.last_run_at = now_utc
                    if item.tipo == 'unica':
                        item.activa = False
                    
                    db.session.commit()
                    print(f"DEBUG SCHEDULER: Completado. Enviados: {len(recipients) if recipients else 0}")
                    
        except Exception as e:
            print(f"ERROR SCHEDULER: {str(e)}")
            db.session.rollback()
