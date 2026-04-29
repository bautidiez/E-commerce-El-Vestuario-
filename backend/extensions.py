from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_compress import Compress
from flask_cors import CORS
from flask_caching import Cache

# Initialize extensions
# Note: db is initialized in models.py to avoid heavy refactor of models for now
jwt = JWTManager()
mail = Mail()
compress = Compress()
cache = Cache()

# Configure CORS - Allow all for easier cross-origin from Vercel
cors = CORS(
    resources={r"/*": {
        "origins": "*",
        "allow_headers": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        "expose_headers": ["Content-Type", "Authorization"]
    }},
    supports_credentials=False
)

# Default limits, can be overridden per route
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=["2000 per day", "500 per hour"]
)
