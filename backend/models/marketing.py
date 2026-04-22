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
