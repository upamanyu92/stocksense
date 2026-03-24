"""
Ollama local LLM model wrapper for stock predictions.
This replaces the Gemini API with local Ollama model (phi-mini).
"""
import requests
import json
import logging
import time
import re
from datetime import datetime

from app.config.ollama_config import OllamaConfig
from app.utils.util import check_index_existence

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_model():
    """Initialize and validate Ollama connection"""
    try:
        logger.info(f"Validating Ollama configuration...")
        OllamaConfig.validate_config()
        logger.info(f"Ollama model '{OllamaConfig.MODEL_NAME}' initialized successfully at {OllamaConfig.OLLAMA_HOST}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Ollama model: {e}")
        raise


def _call_ollama_with_retry(prompt, max_retries=3, delay=2):
    """Call Ollama API with retry logic"""
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{OllamaConfig.OLLAMA_HOST}/api/generate",
                json={
                    "model": OllamaConfig.MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": OllamaConfig.TEMPERATURE,
                    "top_p": OllamaConfig.TOP_P,
                    "top_k": OllamaConfig.TOP_K,
                    "num_predict": OllamaConfig.NUM_PREDICT
                },
                timeout=300  # 5 minute timeout for Ollama response
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API returned status {response.status_code}: {response.text}")

            return response.json()
        except Exception as e:
            logger.warning(f"Ollama API call attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                raise


def _parse_ollama_response(response_data):
    """Parse the Ollama API response to extract prediction data"""
    try:
        text = response_data.get('response', '')
        logger.debug(f"Ollama response text: {text}")

        # Try to extract JSON from the response
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            data = json.loads(json_str)

            # Ensure required fields exist
            if 'predicted_price' in data and 'confidence' in data:
                return {
                    'predicted_price': float(data['predicted_price']),
                    'confidence': float(data['confidence']),
                    'decision': str(data.get('decision', 'caution')),
                    'reasoning': str(data.get('reasoning', ''))
                }

        # Fallback: extract key-value pairs manually
        predicted_price = None
        confidence = None
        decision = None

        # Extract predicted price
        price_match = re.search(r'predicted_price["\']?\s*:\s*([0-9.]+)', text, re.IGNORECASE)
        if price_match:
            predicted_price = float(price_match.group(1))

        # Extract confidence
        conf_match = re.search(r'confidence["\']?\s*:\s*([0-9.]+)', text, re.IGNORECASE)
        if conf_match:
            confidence = float(conf_match.group(1))

        # Extract decision
        decision_match = re.search(r'decision["\']?\s*:\s*["\']?(\w+)', text, re.IGNORECASE)
        if decision_match:
            decision = decision_match.group(1)

        if predicted_price is not None and confidence is not None:
            return {
                'predicted_price': predicted_price,
                'confidence': confidence,
                'decision': decision or 'caution',
                'reasoning': text[:200] if text else ''
            }

        # If no structured data found, return a default response
        logger.warning("No structured prediction data found in Ollama response")
        return {
            'predicted_price': 0.0,
            'confidence': 0.0,
            'decision': 'reject',
            'reasoning': 'Unable to parse response'
        }

    except Exception as e:
        logger.error(f"Error parsing Ollama response: {e}")
        return {
            'predicted_price': 0.0,
            'confidence': 0.0,
            'decision': 'reject',
            'reasoning': f'Parse error: {str(e)}'
        }


def _fetch_stock_history(symbol: str, period_months: int = 1) -> 'pd.DataFrame':
    """
    Fetch recent stock price history via yfinance.
    """
    import yfinance as yf
    period_map = {1: '1mo', 2: '2mo', 3: '3mo', 6: '6mo', 12: '1y'}
    period_str = period_map.get(period_months, '1mo')
    stock = yf.Ticker(symbol)
    hist = stock.history(period=period_str)
    return hist


def predict_with_ollama(symbol):
    """Simple prediction interface using Ollama"""
    try:
        # Get current stock data (Alpha Vantage → yfinance fallback)
        hist = _fetch_stock_history(symbol, period_months=1)
        if hist.empty:
            raise ValueError(f"No data found for symbol {symbol}")

        current_price = hist['Close'].iloc[-1]
        avg_volume = hist['Volume'].mean()

        # Create prompt for Ollama
        prompt = f"""Analyze the following stock data for {symbol} and provide a prediction:

Current Price: {current_price:.2f}
Average Volume: {avg_volume:.0f}
Recent Prices: {hist['Close'].tail(5).tolist()}

Please respond with a JSON object containing:
- predicted_price: Your predicted price for next trading day (must be a number)
- confidence: Confidence level (0.0 to 1.0)
- decision: 'accept', 'caution', or 'reject'

JSON Response:"""

        response_data = _call_ollama_with_retry(prompt)
        result = _parse_ollama_response(response_data)
        return result

    except Exception as e:
        logger.error(f"Error in predict_with_ollama: {e}")
        return {
            'predicted_price': 0.0,
            'confidence': 0.0,
            'decision': 'reject',
            'reasoning': f'Prediction error: {str(e)}'
        }


def predict_with_details(symbol):
    """Enhanced prediction with detailed analysis using Ollama"""
    try:
        # Get current stock data (Alpha Vantage → yfinance fallback)
        hist = _fetch_stock_history(symbol, period_months=3)
        if hist.empty:
            raise ValueError(f"No data found for symbol {symbol}")

        current_price = hist['Close'].iloc[-1]
        avg_volume = hist['Volume'].mean()
        price_change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
        volatility = hist['Close'].pct_change().std() * 100

        # Create detailed prompt for Ollama
        prompt = f"""You are a professional stock analyst. Analyze the following stock data for {symbol} and provide a detailed prediction:

Current Price: {current_price:.2f}
Average Volume: {avg_volume:.0f}
Recent Price Change: {price_change:.2f}%
Volatility (std dev): {volatility:.2f}%
Recent Prices (last 10 days): {hist['Close'].tail(10).tolist()}

Please provide a comprehensive analysis and respond with a JSON object containing:
- predicted_price: Your predicted price for next trading day (must be a number)
- confidence: Confidence level (0.0 to 1.0, where 1.0 is highest confidence)
- decision: 'accept' (high confidence), 'caution' (moderate confidence), or 'reject' (low confidence)
- reasoning: Brief explanation of your analysis

JSON Response:"""

        response_data = _call_ollama_with_retry(prompt)
        result = _parse_ollama_response(response_data)
        return result

    except Exception as e:
        logger.error(f"Error in predict_with_details: {e}")
        return {
            'predicted_price': 0.0,
            'confidence': 0.0,
            'decision': 'reject',
            'reasoning': f'Detailed prediction error: {str(e)}'
        }


def test_ollama():
    """Test Ollama connection and model availability"""
    try:
        prompt = "Hello, test message. Please respond briefly."
        response_data = _call_ollama_with_retry(prompt, max_retries=1)
        logger.info(f"Ollama test successful. Response: {response_data.get('response', '')[:100]}")
        return True
    except Exception as e:
        logger.error(f"Ollama test failed: {e}")
        return False

