from flask_sqlalchemy import SQLAlchemy

# Instancia compartida de SQLAlchemy — se inicializa en app.py con db.init_app(app)
db = SQLAlchemy()
