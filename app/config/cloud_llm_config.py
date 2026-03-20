"""
Configuration for cloud LLM providers (Anthropic, OpenAI, Gemini).

Used when APP_ENV=production. Credentials are read exclusively from
environment variables — never hard-coded in source.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class CloudLLMConfig:
    """Runtime configuration for the active cloud LLM provider."""

    # Which cloud provider to use: "anthropic" | "openai" | "gemini"
    PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()

    # Single API key used by whichever provider is selected
    API_KEY = os.getenv("LLM_API_KEY", "")

    # ── Per-provider model overrides ──────────────────────────────────────────
    # Anthropic
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
    ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
    ANTHROPIC_API_VERSION = "2023-06-01"

    # OpenAI
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

    # Gemini (delegates to existing gemini_config / gemini_model)
    GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")

    # ── Generation parameters ─────────────────────────────────────────────────
    TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))

    # ── Retry behaviour ───────────────────────────────────────────────────────
    MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
    RETRY_DELAY = int(os.getenv("LLM_RETRY_DELAY", "2"))

    @classmethod
    def validate_config(cls) -> bool:
        """Raise ValueError when required configuration is missing."""
        if not cls.API_KEY:
            raise ValueError(
                "LLM_API_KEY environment variable is not set. "
                "Please set it before running the application in production mode."
            )
        if cls.PROVIDER not in ("anthropic", "openai", "gemini"):
            raise ValueError(
                f"Unsupported LLM_PROVIDER '{cls.PROVIDER}'. "
                "Allowed values: anthropic, openai, gemini."
            )
        return True
