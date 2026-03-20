import logging
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

    # Alpha Vantage stock data API
    ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', '')

    # Debug mode
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    # Flask settings
    FLASK_HOST = '0.0.0.0'
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5005))

    # ── Runtime environment ───────────────────────────────────────────────────
    # Controls which LLM backend is used:
    #   "dev"        → local Ollama  (default)
    #   "production" → cloud LLM (see LLM_PROVIDER / LLM_API_KEY)
    APP_ENV = os.getenv('APP_ENV', 'dev').strip().lower()

    # ── Ollama AI Configuration (dev / local LLM) ─────────────────────────────
    OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'phi3:mini')

    # ── Cloud LLM Configuration (production) ─────────────────────────────────
    # LLM_PROVIDER: "anthropic" | "openai" | "gemini"
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'gemini').lower()
    # Single API key for whichever cloud provider is selected
    LLM_API_KEY = os.getenv('LLM_API_KEY', '')

    @classmethod
    def is_production(cls) -> bool:
        """Return True when the application is running in production mode."""
        return cls.APP_ENV == 'production'

    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist."""
        os.makedirs(cls.DB_DIR, exist_ok=True)
        os.makedirs(cls.MODEL_DIR, exist_ok=True)

    @classmethod
    def initialize_llm(cls):
        """Initialize the appropriate LLM backend based on APP_ENV."""
        if cls.is_production():
            from app.models.cloud_llm_model import call_cloud_llm  # noqa: F401
            from app.config.cloud_llm_config import CloudLLMConfig
            try:
                CloudLLMConfig.validate_config()
                logging.info(
                    f"Cloud LLM initialized: provider={CloudLLMConfig.PROVIDER}"
                )
                return True
            except Exception as e:
                logging.warning(
                    f"Cloud LLM configuration invalid: {e}. "
                    "Predictions will not work until LLM_PROVIDER and LLM_API_KEY are set."
                )
                return False
        else:
            from app.models.ollama_model import initialize_model
            try:
                initialize_model()
                return True
            except Exception as e:
                logging.warning(
                    f"Failed to initialize Ollama: {e}. "
                    "Predictions may not work until Ollama is running."
                )
                return False

    # Keep backward-compatible alias used by existing code
    @classmethod
    def initialize_ollama(cls):
        """Backward-compatible alias for initialize_llm()."""
        return cls.initialize_llm()
