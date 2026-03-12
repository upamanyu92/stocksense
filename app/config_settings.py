import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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

    # Gemini AI Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist."""
        os.makedirs(cls.DB_DIR, exist_ok=True)
        os.makedirs(cls.MODEL_DIR, exist_ok=True)

    @classmethod
    def initialize_gemini(cls):
        """Initialize Gemini AI API"""
        from app.models.gemini_model import initialize_model
        try:
            initialize_model()
            return True
        except Exception as e:
            import logging
            logging.warning(f"Failed to initialize Gemini: {e}. Predictions may not work until API key is configured.")
            return False
