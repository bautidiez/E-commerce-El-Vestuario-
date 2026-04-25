from datetime import datetime
from .base import db

class NewsletterHistory(db.Model):
    """Modelo para historial de emails de newsletter enviados"""
    __tablename__ = 'newsletter_history'

    id = db.Column(db.Integer, primary_key=True)
    asunto = db.Column(db.String(200), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_count = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'asunto': self.asunto,
            'contenido': self.contenido,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'sent_count': self.sent_count
        }

class ScheduledNewsletter(db.Model):
    """Modelo para programar envíos de newsletter"""
    __tablename__ = 'scheduled_newsletters'

    id = db.Column(db.Integer, primary_key=True)
    asunto = db.Column(db.String(200), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    
    # Tipo: 'unica', 'semanal', 'mensual'
    tipo = db.Column(db.String(20), nullable=False, default='unica')
    
    # Para 'unica': fecha y hora
    scheduled_at = db.Column(db.DateTime, nullable=True)
    
    # Para 'semanal': día de la semana (0-6, 0=Lunes)
    dia_semana = db.Column(db.Integer, nullable=True)
    
    # Para 'mensual': posición (1=Primero, 2=Segundo, etc.) y día
    posicion_mes = db.Column(db.Integer, nullable=True) # 1, 2, 3, 4, 5 (5=último)
    
    # Hora común para recurrentes (HH:MM)
    hora_envio = db.Column(db.String(5), nullable=True)
    
    activa = db.Column(db.Boolean, default=True)
    last_run_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'asunto': self.asunto,
            'contenido': self.contenido,
            'tipo': self.tipo,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'dia_semana': self.dia_semana,
            'posicion_mes': self.posicion_mes,
            'hora_envio': self.hora_envio,
            'activa': self.activa,
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
