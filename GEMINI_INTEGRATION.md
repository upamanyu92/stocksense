# Google Gemini AI Integration for StockSense

## Overview

StockSense has been updated to use **Google Generative AI (Gemini)** for stock price predictions and technical analysis, replacing the previous Keras/TensorFlow neural network models.

## Benefits of Gemini Integration

1. **No Model Training Required**: Eliminates the need for data collection, feature engineering, and model training pipelines
2. **Advanced Analysis**: Leverages Gemini's large language model for sophisticated technical and fundamental analysis
3. **Real-time Decision Making**: Provides confidence scores and investment decisions based on current market data
4. **Adaptive Reasoning**: Returns detailed reasoning for each prediction
5. **Lower Computational Overhead**: No GPU/CPU intensive training processes

## Setup Instructions

### 1. Get Google Generative AI API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click "Get API Key" or "Create API Key"
3. Copy your API key

### 2. Configure Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` and set your API key:

```bash
GEMINI_API_KEY=your_actual_api_key_here
GEMINI_MODEL_NAME=gemini-pro
GEMINI_TEMPERATURE=0.7
GEMINI_TOP_P=0.9
GEMINI_TOP_K=40
GEMINI_MAX_OUTPUT_TOKENS=1024
GEMINI_MIN_CONFIDENCE=0.6
GEMINI_HIGH_CONFIDENCE_THRESHOLD=0.8
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

The `google-generativeai` package is now included in requirements.txt.

### 4. Update .gitignore

Make sure `.env` is in your `.gitignore` to avoid committing API keys:

```bash
echo ".env" >> .gitignore
```

## How It Works

### Prediction Flow

```
1. Stock Data Download (NSE via yfinance)
   ↓
2. Feature Enrichment (SMA, EMA, RSI, MACD, Volume Analysis)
   ↓
3. Data Enrichment Agent (Prepares comprehensive context)
   ↓
4. Gemini API Analysis (Technical & Fundamental)
   ↓
5. Ensemble Prediction (Combines multiple Gemini perspectives)
   ↓
6. Adaptive Learning (Updates prediction strategies)
   ↓
7. Decision Making (Accept/Caution/Reject)
   ↓
8. Database Storage & WebSocket Broadcast
```

### Key Components

#### `app/models/gemini_model.py`
- Core Gemini API wrapper
- Handles API calls with retry logic
- Parses Gemini responses into structured predictions
- Prepares enriched technical context for analysis

#### `app/config/gemini_config.py`
- Configuration management for Gemini API
- Environment variable handling
- Prompt templates for stock analysis
- Model parameters and thresholds

#### `app/agents/ensemble_agent.py`
- Uses multiple Gemini API calls with different perspectives
- Combines predictions using weighted averaging
- Calculates confidence intervals and uncertainty

#### `app/services/prediction_service.py`
- Entry point for prediction execution
- Integrates with PredictionCoordinator
- Stores results in database
- Broadcasts updates via WebSocket

## Technical Indicators Used

The system provides Gemini with the following technical indicators:

- **Moving Averages**: SMA (20, 50), EMA (20, 50)
- **Momentum**: RSI (14), MACD
- **Volume Analysis**: Average volume, volume trends
- **Price Levels**: 52-week highs/lows, current price
- **Performance Metrics**: 7-day and 30-day price changes, volatility

## API Response Format

### Prediction Result

```json
{
  "predicted_price": 1500.50,
  "confidence": 0.82,
  "decision": "accept",
  "market_sentiment": "bullish",
  "technical_signals": "strong",
  "risk_level": "low",
  "reasoning": "Stock showing strong uptrend with RSI above 60...",
  "timestamp": "2024-03-01T10:30:00",
  "model": "gemini-pro"
}
```

### Decision Categories

- **accept**: High confidence prediction (score > 0.75)
- **caution**: Moderate confidence prediction (0.6 <= score <= 0.75)
- **reject**: Low confidence prediction (score < 0.6)

## Configuration Options

### Temperature (0.0 - 2.0)
- **Lower (0.0-0.5)**: More deterministic, consistent predictions
- **Higher (0.7-1.5)**: More creative, diverse analysis
- **Recommended**: 0.7

### Top P (0.0 - 1.0)
- Controls diversity of predictions
- Recommended: 0.9

### Top K (1 - 40)
- Limits vocabulary choice
- Recommended: 40

## Monitoring and Debugging

### Enable Debug Logging

```bash
DEBUG=True python -m app.main
```

### Check Gemini API Status

```python
from app.models.gemini_model import initialize_model
model = initialize_model()
# If no error, API is working
```

### View Prediction Logs

Predictions are logged with:
- Symbol being analyzed
- Gemini response details
- Confidence scores
- Decision rationale

## Error Handling

### Common Issues

1. **"GEMINI_API_KEY environment variable not set"**
   - Solution: Add your API key to `.env` file

2. **"Failed to parse Gemini JSON response"**
   - Gemini response wasn't in expected format
   - Check Gemini API status
   - Increase MAX_OUTPUT_TOKENS if response is truncated

3. **"All retries exhausted"**
   - Network or API issue
   - Check internet connection
   - Verify API key is valid
   - Check Google Generative AI service status

## Migration from Keras Models

### What Changed

| Aspect | Before | After |
|--------|--------|-------|
| Model Training | TensorFlow/Keras neural networks | N/A (API-based) |
| Model Files | Saved .h5 and .pkl files | No local model files |
| Prediction Time | ~1-5 seconds per stock | ~2-10 seconds per stock |
| Accuracy | Dependent on training data | Leverages LLM understanding |
| Maintenance | Requires model retraining | Automatic via API updates |

### Backward Compatibility

- Database schema remains unchanged
- Prediction API response format identical
- All downstream services work without modification
- Dashboard, WebSocket, and API endpoints unchanged

## Advanced Configuration

### Custom Prompts

Edit `GeminiConfig.FEATURE_ANALYSIS_PROMPT` in `app/config/gemini_config.py`:

```python
FEATURE_ANALYSIS_PROMPT = """
Your custom prompt here...
"""
```

### Adaptive Learning

The `AdaptiveLearningAgent` automatically adjusts weights based on:
- Prediction accuracy
- Market regime changes
- Volatility patterns

## Performance Considerations

- **API Calls**: Each prediction = 1-2 Gemini API calls
- **Response Time**: 2-10 seconds per stock (network dependent)
- **Rate Limits**: Check Google's API quotas
- **Cost**: Pricing based on API token usage

## Future Enhancements

Potential improvements:
- Multi-model ensemble with different LLMs
- Fine-tuned prompts for different market conditions
- Caching of similar predictions
- Integration with other AI models (Claude, GPT-4, etc.)
- Real-time sentiment analysis from news

## Support & Troubleshooting

For issues:
1. Check logs: `tail -f logs/stocksense.log`
2. Verify `.env` configuration
3. Test API key: `curl https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key=YOUR_KEY`
4. Check internet connectivity

