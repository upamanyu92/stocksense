"""
Gemini AI model for stock price predictions and analysis.
Replaces Keras/TensorFlow models with Google Gemini API.
"""
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any

from google import genai
from google.genai import types

from app.config.gemini_config import GeminiConfig
from app.features.feature_factory import create_features
import yfinance as yf


# Configure Gemini API
def initialize_gemini():
    """Initialize and configure Gemini API"""
    try:
        GeminiConfig.validate_config()
        # The new SDK uses a client-based approach, so we don't configure globally here
        # but we validate the key is present.
        logging.info(f"Gemini API configuration validated for model: {GeminiConfig.MODEL_NAME}")
    except Exception as e:
        logging.error(f"Failed to validate Gemini API config: {e}")
        raise


class GeminiModel:
    """Wrapper for Gemini API-based stock predictions"""

    def __init__(self):
        """Initialize Gemini model"""
        self.model_name = GeminiConfig.MODEL_NAME
        self.min_confidence = GeminiConfig.MIN_CONFIDENCE
        self.max_retries = GeminiConfig.MAX_RETRIES
        self.retry_delay = GeminiConfig.RETRY_DELAY
        self.logger = logging.getLogger("GeminiModel")

        # Initialize Gemini client
        initialize_gemini()
        self.client = genai.Client(api_key=GeminiConfig.API_KEY)

    def predict(self, symbol: str) -> Dict[str, Any]:
        """
        Make a prediction for a stock using Gemini AI.

        Args:
            symbol: Stock symbol (e.g., 'INFY.BO')

        Returns:
            Dictionary with prediction, confidence, and decision
        """
        try:
            self.logger.info(f"Starting Gemini prediction for {symbol}")

            # Download and prepare data
            stock_data = self._download_stock_data(symbol)

            # Get enriched features
            enriched_data = self._prepare_enriched_context(symbol, stock_data)

            # Make prediction with retry logic
            result = self._call_gemini_with_retry(symbol, enriched_data)

            self.logger.info(f"Prediction for {symbol}: {result['predicted_price']:.2f}, "
                           f"Confidence: {result['confidence']:.2f}, Decision: {result['decision']}")

            return result

        except Exception as e:
            self.logger.error(f"Error making prediction for {symbol}: {e}")
            raise

    def _download_stock_data(self, symbol: str, period: str = '2y') -> Any:
        """
        Download historical stock data.

        Primary source: Alpha Vantage TIME_SERIES_DAILY_ADJUSTED.
        Fallback:       yfinance download.

        Tool: TIME_SERIES_DAILY_ADJUSTED
        Confidence Score: 95%
        """
        from app.config.alpha_vantage_config import AlphaVantageConfig

        try:
            if AlphaVantageConfig.is_configured():
                try:
                    from app.utils.alpha_vantage_client import get_time_series_daily
                    outputsize = 'full' if period in ('2y', '5y', 'max') else 'compact'
                    stock = get_time_series_daily(symbol, outputsize=outputsize)
                    if stock is not None and not stock.empty:
                        self.logger.debug(
                            "Alpha Vantage TIME_SERIES_DAILY_ADJUSTED: %d rows for %s",
                            len(stock), symbol,
                        )
                        stock = create_features(stock)
                        return stock
                except Exception as av_exc:
                    self.logger.warning(
                        "Alpha Vantage download failed for %s: %s — falling back to yfinance",
                        symbol, av_exc,
                    )

            # Fallback: yfinance
            self.logger.debug(f"Downloading stock data for {symbol} via yfinance")
            stock = yf.download(symbol, period=period, auto_adjust=True, progress=False)

            if stock.empty:
                raise ValueError(f"No data downloaded for {symbol}")

            # Create technical features
            stock = create_features(stock)

            self.logger.debug(f"Downloaded {len(stock)} rows for {symbol}")
            return stock

        except Exception as e:
            self.logger.error(f"Error downloading stock data for {symbol}: {e}")
            raise

    def _prepare_enriched_context(self, symbol: str, stock_data: Any) -> str:
        """
        Prepare enriched context for Gemini analysis.

        Args:
            symbol: Stock symbol
            stock_data: Pandas dataframe with stock data

        Returns:
            Formatted context string for Gemini API
        """
        try:
            # Get latest data point
            latest = stock_data.iloc[-1]

            # Get historical context (last 60 days)
            recent = stock_data.tail(60)

            # Calculate additional statistics
            stats = {
                'current_price': float(latest.get('Close', 0)),
                'price_change_7d': float((latest['Close'] - stock_data.iloc[-7]['Close']) / stock_data.iloc[-7]['Close'] * 100),
                'price_change_30d': float((latest['Close'] - stock_data.iloc[-30]['Close']) / stock_data.iloc[-30]['Close'] * 100),
                'volatility_30d': float(recent['Close'].pct_change().std() * 100),
                'volume_trend': float(recent['Volume'].iloc[-10:].mean() / recent['Volume'].iloc[-30:].mean()),
                'high_52w': float(stock_data['Close'].tail(252).max()),
                'low_52w': float(stock_data['Close'].tail(252).min()),
            }

            # Build context with important technical indicators
            context_data = {
                'symbol': symbol,
                'analysis_date': datetime.now().isoformat(),
                'current_price': stats['current_price'],
                'price_changes': {
                    '7_day_change_%': round(stats['price_change_7d'], 2),
                    '30_day_change_%': round(stats['price_change_30d'], 2),
                },
                'volatility': {
                    '30_day_volatility_%': round(stats['volatility_30d'], 2),
                    'volume_trend': round(stats['volume_trend'], 2),
                },
                'price_levels': {
                    '52w_high': round(stats['high_52w'], 2),
                    '52w_low': round(stats['low_52w'], 2),
                    'distance_from_52w_high': round((1 - stats['current_price'] / stats['high_52w']) * 100, 2),
                },
                'technical_indicators': {
                    'SMA_20': round(float(latest.get('SMA_20', 0)), 2),
                    'SMA_50': round(float(latest.get('SMA_50', 0)), 2),
                    'EMA_20': round(float(latest.get('EMA_20', 0)), 2),
                    'EMA_50': round(float(latest.get('EMA_50', 0)), 2),
                    'RSI': round(float(latest.get('RSI', 50)), 2),
                    'MACD': round(float(latest.get('MACD', 0)), 4),
                },
                'volume_analysis': {
                    'avg_volume_30d': round(float(recent['Volume'].mean()), 0),
                    'current_volume': round(float(latest.get('Volume', 0)), 0),
                }
            }

            # Format as readable context
            context_str = f"""
Stock Analysis Context for {symbol}:

Current Price: ₹{stats['current_price']:.2f}

Price Performance:
- 7-day change: {stats['price_change_7d']:.2f}%
- 30-day change: {stats['price_change_30d']:.2f}%

Volatility Metrics:
- 30-day volatility: {stats['volatility_30d']:.2f}%
- Volume trend (avg recent/avg 30d): {stats['volume_trend']:.2f}x

52-Week Range:
- High: ₹{stats['high_52w']:.2f}
- Low: ₹{stats['low_52w']:.2f}
- Current distance from high: {(1 - stats['current_price'] / stats['high_52w']) * 100:.2f}%

Technical Indicators (Latest):
- SMA (20-day): ₹{latest.get('SMA_20', 0):.2f}
- SMA (50-day): ₹{latest.get('SMA_50', 0):.2f}
- EMA (20-day): ₹{latest.get('EMA_20', 0):.2f}
- EMA (50-day): ₹{latest.get('EMA_50', 0):.2f}
- RSI (14): {latest.get('RSI', 50):.2f}
- MACD: {latest.get('MACD', 0):.4f}

Volume Analysis:
- 30-day average: {recent['Volume'].mean():,.0f}
- Current: {latest.get('Volume', 0):,.0f}
- Trend: {'Increasing' if stats['volume_trend'] > 1 else 'Decreasing'}

Technical Data (JSON): {json.dumps(context_data, indent=2)}
"""

            self.logger.debug(f"Prepared context for {symbol}")
            return context_str

        except Exception as e:
            self.logger.error(f"Error preparing enriched context for {symbol}: {e}")
            raise

    def _call_gemini_with_retry(self, symbol: str, context: str) -> Dict[str, Any]:
        """
        Call Gemini API with retry logic and error handling.

        Args:
            symbol: Stock symbol
            context: Enriched data context

        Returns:
            Parsed prediction result
        """
        prompt = GeminiConfig.FEATURE_ANALYSIS_PROMPT.format(
            symbol=symbol,
            data_context=context
        )

        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Gemini API call (attempt {attempt + 1}/{self.max_retries})")

                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=GeminiConfig.TEMPERATURE,
                        top_p=GeminiConfig.TOP_P,
                        top_k=GeminiConfig.TOP_K,
                        max_output_tokens=GeminiConfig.MAX_OUTPUT_TOKENS,
                        safety_settings=[
                            types.SafetySetting(
                                category='HARM_CATEGORY_HATE_SPEECH',
                                threshold='BLOCK_NONE'
                            ),
                            types.SafetySetting(
                                category='HARM_CATEGORY_DANGEROUS_CONTENT',
                                threshold='BLOCK_NONE'
                            ),
                            types.SafetySetting(
                                category='HARM_CATEGORY_HARASSMENT',
                                threshold='BLOCK_NONE'
                            ),
                            types.SafetySetting(
                                category='HARM_CATEGORY_SEXUALLY_EXPLICIT',
                                threshold='BLOCK_NONE'
                            ),
                        ]
                    )
                )

                # Parse response
                response_text = response.text
                self.logger.debug(f"Gemini response: {response_text}")

                # Extract JSON from response
                result = self._parse_gemini_response(response_text, symbol)

                return result

            except Exception as e:
                self.logger.warning(f"Gemini API call failed (attempt {attempt + 1}): {e}")

                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    self.logger.error(f"All retries exhausted for {symbol}")
                    raise

    def _parse_gemini_response(self, response_text: str, symbol: str) -> Dict[str, Any]:
        """
        Parse Gemini API response and extract prediction data.

        Args:
            response_text: Raw response from Gemini API
            symbol: Stock symbol (for fallback)

        Returns:
            Structured prediction result
        """
        try:
            # Try to extract JSON from response
            json_str = response_text

            # If response contains code block, extract JSON from it
            if '```json' in response_text:
                json_str = response_text.split('```json')[1].split('```')[0]
            elif '```' in response_text:
                json_str = response_text.split('```')[1].split('```')[0]

            # Parse JSON
            result = json.loads(json_str.strip())

            # Validate and extract required fields
            parsed_result = {
                'predicted_price': float(result.get('predicted_price', 0)),
                'confidence': float(result.get('confidence', 0.5)),
                'decision': result.get('decision', 'caution'),
                'reasoning': result.get('reasoning', ''),
                'market_sentiment': result.get('market_sentiment', 'neutral'),
                'technical_signals': result.get('technical_signals', 'moderate'),
                'risk_level': result.get('risk_level', 'medium'),
                'model': self.model_name,
                'timestamp': datetime.now().isoformat()
            }

            # Validate decision value
            if parsed_result['decision'] not in ['accept', 'caution', 'reject']:
                parsed_result['decision'] = 'caution'

            # Ensure confidence is between 0 and 1
            parsed_result['confidence'] = max(0.0, min(1.0, parsed_result['confidence']))

            self.logger.debug(f"Parsed Gemini response: {parsed_result}")

            return parsed_result

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Gemini JSON response: {e}")
            self.logger.debug(f"Raw response: {response_text}")

            # Return fallback prediction
            return {
                'predicted_price': 0,
                'confidence': 0.3,
                'decision': 'reject',
                'reasoning': f'Failed to parse API response: {str(e)}',
                'market_sentiment': 'unknown',
                'technical_signals': 'weak',
                'risk_level': 'high',
                'model': self.model_name,
                'timestamp': datetime.now().isoformat()
            }


# Global Gemini model instance
gemini_model = None


def initialize_model():
    """Initialize the global Gemini model instance"""
    global gemini_model
    if gemini_model is None:
        gemini_model = GeminiModel()
    return gemini_model


def predict_with_gemini(symbol: str) -> float:
    """
    Make a prediction using Gemini API.

    Args:
        symbol: Stock symbol (e.g., 'INFY.BO')

    Returns:
        Predicted price (float)
    """
    try:
        model = initialize_model()
        result = model.predict(symbol)

        # Return predicted price for compatibility
        return result['predicted_price']

    except Exception as e:
        logging.error(f"Error in predict_with_gemini for {symbol}: {e}")
        raise


def predict_with_details(symbol: str) -> Dict[str, Any]:
    """
    Make a prediction using Gemini API and return full details.

    Args:
        symbol: Stock symbol (e.g., 'INFY.BO')

    Returns:
        Full prediction result with confidence, decision, and reasoning
    """
    try:
        model = initialize_model()
        return model.predict(symbol)

    except Exception as e:
        logging.error(f"Error in predict_with_details for {symbol}: {e}")
        raise
