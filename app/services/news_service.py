import logging
from typing import List, Dict

NEWS_API_KEY = None  # configure via .env if available


def fetch_latest_news(symbol: str, limit: int = 10) -> List[Dict]:
    """Fetch latest news items for a symbol. If no API configured, return empty list."""
    logging.info(f'Fetch news for {symbol}')
    # Placeholder: in future integrate with NewsAPI or other providers
    return []


def analyze_sentiment(texts: List[str]) -> Dict:
    """Stub: analyze sentiment using Gemini or simple heuristics"""
    # For now return neutral
    return {'sentiment': 'neutral', 'score': 0.5}

