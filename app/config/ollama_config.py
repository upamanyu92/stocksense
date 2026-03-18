"""
Configuration for Ollama local LLM integration for stock predictions.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class OllamaConfig:
    """Configuration for Ollama local LLM"""

    # Ollama API Configuration
    OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    MODEL_NAME = os.getenv('OLLAMA_MODEL_NAME', 'phi-mini')

    # Temperature and generation parameters
    TEMPERATURE = float(os.getenv('OLLAMA_TEMPERATURE', '0.7'))
    TOP_P = float(os.getenv('OLLAMA_TOP_P', '0.9'))
    TOP_K = int(os.getenv('OLLAMA_TOP_K', '40'))
    NUM_PREDICT = int(os.getenv('OLLAMA_NUM_PREDICT', '500'))  # Max tokens to generate

    # Prediction confidence thresholds
    MIN_CONFIDENCE = float(os.getenv('OLLAMA_MIN_CONFIDENCE', '0.5'))
    HIGH_CONFIDENCE_THRESHOLD = float(os.getenv('OLLAMA_HIGH_CONFIDENCE_THRESHOLD', '0.8'))

    # System prompts for stock analysis
    STOCK_ANALYSIS_SYSTEM_PROMPT = """You are an expert stock market analyst with deep knowledge of technical analysis, 
fundamental analysis, and market dynamics. You analyze stock data and provide:
1. A predicted price in 30 days (numerical value)
2. Confidence level (0.0 to 1.0)
3. Decision: 'accept', 'caution', or 'reject'
4. Detailed reasoning for your prediction

Respond in JSON format with keys: predicted_price, confidence, decision, reasoning."""

    FEATURE_ANALYSIS_PROMPT = """Given the following technical indicators and market data for {symbol}:

{data_context}

Based on this data, provide:
1. Current market sentiment (bullish/bearish/neutral)
2. Key technical signals (strong/moderate/weak)
3. Risk assessment (high/medium/low)
4. Predicted price for next 30 days as a specific number
5. Confidence in this prediction (0.0 to 1.0)
6. Decision: 'accept', 'caution', or 'reject'

Respond in valid JSON format with keys: market_sentiment, technical_signals, risk_level, 
predicted_price (number), confidence (number), decision (string), reasoning (string)."""

    # API retry configuration
    MAX_RETRIES = int(os.getenv('OLLAMA_MAX_RETRIES', '3'))
    RETRY_DELAY = int(os.getenv('OLLAMA_RETRY_DELAY', '2'))  # seconds

    # Feature importance for analysis
    IMPORTANT_FEATURES = [
        'current_value',
        'SMA_20',
        'SMA_50',
        'EMA_20',
        'EMA_50',
        'RSI',
        'MACD',
        'Volume_Mean',
        'change',
        'pChange',
        'dayHigh',
        'dayLow'
    ]

    @classmethod
    def validate_config(cls):
        """Validate that Ollama is running and the model is available"""
        try:
            import requests
            response = requests.get(f"{cls.OLLAMA_HOST}/api/tags", timeout=5)
            if response.status_code != 200:
                raise ValueError(f"Ollama API returned status {response.status_code}")

            models = response.json().get('models', [])
            model_names = [m.get('name', '') for m in models]

            if not any(cls.MODEL_NAME in name for name in model_names):
                raise ValueError(
                    f"Model '{cls.MODEL_NAME}' not found in Ollama. "
                    f"Available models: {model_names}. "
                    f"Please run: ollama pull {cls.MODEL_NAME}"
                )
            return True
        except Exception as e:
            raise ValueError(f"Ollama configuration validation failed: {e}")

