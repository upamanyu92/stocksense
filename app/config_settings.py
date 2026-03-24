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
    FLASK_HOST = '0.0.0.0'  # nosec B104 – intentional: containerised deployment requires all-interface binding
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5005))
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL_NAME', 'phi4-mini')

    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist."""
        os.makedirs(cls.DB_DIR, exist_ok=True)
        os.makedirs(cls.MODEL_DIR, exist_ok=True)

    @classmethod
    def initialize_ollama(cls):
        """Initialize Ollama local LLM"""
        from app.models.ollama_model import initialize_model
        try:
            initialize_model()
            return True
        except Exception as e:
            import logging
            logging.warning(f"Failed to initialize Ollama: {e}. Predictions may not work until Ollama is running.")
            return False
