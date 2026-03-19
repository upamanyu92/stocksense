"""
Configuration for Google Gemini AI API integration for stock predictions.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class GeminiConfig:
    """Configuration for Gemini API"""

    # API Configuration
    API_KEY = os.getenv('GEMINI_API_KEY', '')
    # Using gemini-2.0-flash as it's the current stable version
    MODEL_NAME = os.getenv('GEMINI_MODEL_NAME', 'gemini-2.0-flash')

    # Temperature and generation parameters
    TEMPERATURE = float(os.getenv('GEMINI_TEMPERATURE', '0.7'))
    TOP_P = float(os.getenv('GEMINI_TOP_P', '0.9'))
    TOP_K = int(os.getenv('GEMINI_TOP_K', '40'))
    MAX_OUTPUT_TOKENS = int(os.getenv('GEMINI_MAX_OUTPUT_TOKENS', '1024'))

    # Prediction confidence thresholds
    MIN_CONFIDENCE = float(os.getenv('GEMINI_MIN_CONFIDENCE', '0.5'))
    HIGH_CONFIDENCE_THRESHOLD = float(os.getenv('GEMINI_HIGH_CONFIDENCE_THRESHOLD', '0.8'))

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
    MAX_RETRIES = int(os.getenv('GEMINI_MAX_RETRIES', '3'))
    RETRY_DELAY = int(os.getenv('GEMINI_RETRY_DELAY', '2'))  # seconds

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
        """Validate that required configuration is present"""
        if not cls.API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable not set. "
                           "Please set it before running the application.")
        return True
