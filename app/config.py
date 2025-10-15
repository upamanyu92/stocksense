import os

class Config:
    # Base paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Database
    DB_DIR = os.path.join(BASE_DIR, 'app', 'db')
    DB_PATH = os.path.join(DB_DIR, 'stock_predictions.db')

    # Model paths
    MODEL_DIR = os.path.join(BASE_DIR, 'model', 'saved_models')

    # Debug mode
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    # Flask settings
    FLASK_HOST = '0.0.0.0'
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5005))

    # SSL/HTTPS settings
    USE_SSL = os.getenv('USE_SSL', 'True').lower() == 'true'
    SSL_CERT_DIR = os.path.join(BASE_DIR, 'certs')
    SSL_CERT_PATH = os.getenv('SSL_CERT_PATH', os.path.join(SSL_CERT_DIR, 'cert.pem'))
    SSL_KEY_PATH = os.getenv('SSL_KEY_PATH', os.path.join(SSL_CERT_DIR, 'key.pem'))

    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist."""
        os.makedirs(cls.DB_DIR, exist_ok=True)
        os.makedirs(cls.MODEL_DIR, exist_ok=True)
        os.makedirs(cls.SSL_CERT_DIR, exist_ok=True)

    @classmethod
    def get_ssl_context(cls):
        """
        Get SSL context for HTTPS if SSL is enabled and certificates exist.
        Returns None if SSL is disabled or certificates don't exist.
        """
        if not cls.USE_SSL:
            return None
        
        if os.path.exists(cls.SSL_CERT_PATH) and os.path.exists(cls.SSL_KEY_PATH):
            return (cls.SSL_CERT_PATH, cls.SSL_KEY_PATH)
        
        return None

