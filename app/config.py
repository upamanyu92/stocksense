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

    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist."""
        os.makedirs(cls.DB_DIR, exist_ok=True)
        os.makedirs(cls.MODEL_DIR, exist_ok=True)
