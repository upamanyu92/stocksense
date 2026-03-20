"""
LLM Factory for StockSense.

Selects the appropriate LLM backend based on the APP_ENV environment variable:

  APP_ENV=dev (default)
    → Ollama running locally (optimised for Apple Silicon M1/M2)
    → Reads: OLLAMA_HOST, OLLAMA_MODEL

  APP_ENV=production
    → Cloud LLM provider (Anthropic / OpenAI / Gemini)
    → Reads: LLM_PROVIDER, LLM_API_KEY

Usage
-----
  from app.models.llm_factory import LLMFactory

  # Generate free-form text
  text = LLMFactory.generate(prompt)

  # Stock-specific prediction helper
  result = LLMFactory.predict_with_details(symbol)
"""
import logging
import os

logger = logging.getLogger(__name__)

# ── Environment detection ─────────────────────────────────────────────────────

def _is_production() -> bool:
    """Return True when running in production mode."""
    return os.getenv("APP_ENV", "dev").strip().lower() == "production"


# ── Public factory interface ──────────────────────────────────────────────────

class LLMFactory:
    """
    Thin factory that routes LLM calls to the correct backend at runtime.

    All methods are static so callers do not need to instantiate the class.
    """

    @staticmethod
    def generate(prompt: str, **kwargs) -> str:
        """
        Generate a text completion for *prompt* using the active LLM backend.

        Args:
            prompt: The prompt to send to the LLM.
            **kwargs: Extra keyword arguments forwarded to the backend call
                      (e.g. max_retries, delay for Ollama).

        Returns:
            Raw text response from the model.
        """
        if _is_production():
            logger.debug("LLMFactory: routing generate() to cloud LLM")
            from app.models.cloud_llm_model import call_cloud_llm
            return call_cloud_llm(prompt)
        else:
            logger.debug("LLMFactory: routing generate() to Ollama")
            from app.models.ollama_model import _call_ollama_with_retry
            response = _call_ollama_with_retry(
                prompt,
                max_retries=kwargs.get("max_retries", 3),
                delay=kwargs.get("delay", 2),
            )
            return response.get("response", "")

    @staticmethod
    def predict_with_details(symbol: str) -> dict:
        """
        Return a structured stock prediction for *symbol*.

        Returns:
            Dict with keys: predicted_price, confidence, decision, reasoning.
        """
        if _is_production():
            logger.debug("LLMFactory: routing predict_with_details() to cloud LLM")
            from app.models.cloud_llm_model import predict_with_details
            return predict_with_details(symbol)
        else:
            logger.debug("LLMFactory: routing predict_with_details() to Ollama")
            from app.models.ollama_model import predict_with_details
            return predict_with_details(symbol)

    @staticmethod
    def active_backend() -> str:
        """Return a human-readable label for the currently active backend."""
        if _is_production():
            from app.config.cloud_llm_config import CloudLLMConfig
            return f"cloud:{CloudLLMConfig.PROVIDER}"
        return "ollama"
