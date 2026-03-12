# Quick Start Guide - Gemini AI Integration

## 5-Minute Setup

### Step 1: Get Your API Key (2 minutes)
1. Visit: https://aistudio.google.com/app/apikey
2. Click "Get API Key" or "Create API Key"
3. Copy the API key

### Step 2: Configure Environment (1 minute)
```bash
# Copy the example config
cp .env.example .env

# Edit .env and set your API key
# Replace: GEMINI_API_KEY=your_google_generativeai_api_key_here
# With your actual key
nano .env
```

### Step 3: Install Dependencies (2 minutes)
```bash
# Run the setup script
bash setup_gemini.sh

# Or manually install
pip install -r requirements.txt
```

### Step 4: Start the Application
```bash
python -m app.main
```

The app will start at: **http://localhost:5005**

---

## How Gemini AI Predictions Work

### Traditional Keras Model (OLD)
```
Download Data → Train Neural Network → Save Model → Make Prediction
(Slow, requires retraining)
```

### New Gemini AI Approach
```
Download Data → Prepare Features → Send to Gemini API → Get Prediction
(Fast, no retraining needed)
```

### What Happens During a Prediction

1. **Data Download** (2-3 seconds)
   - Downloads 2 years of historical data from NSE via yfinance
   - Calculates technical indicators (SMA, EMA, RSI, MACD, Volume)

2. **Feature Enrichment** (1 second)
   - Prepares comprehensive market context
   - Calculates 52-week highs/lows, volatility, trends

3. **Gemini Analysis** (3-5 seconds)
   - Sends enriched data to Google Gemini API
   - Gets back:
     - Predicted price for next 30 days
     - Confidence score (0.0-1.0)
     - Decision (accept/caution/reject)
     - Market sentiment and risk level
     - Detailed reasoning

4. **Adaptive Learning** (1 second)
   - Adjusts future predictions based on accuracy
   - Tracks market regime changes

5. **Database Storage** (<1 second)
   - Saves prediction to database
   - Broadcasts via WebSocket to dashboard

**Total time per stock: 7-10 seconds**

---

## Example Prediction Response

```json
{
  "symbol": "INFY.BO",
  "predicted_price": 1650.75,
  "confidence": 0.82,
  "decision": "accept",
  "market_sentiment": "bullish",
  "technical_signals": "strong",
  "risk_level": "low",
  "reasoning": "Stock showing strong uptrend with RSI above 60, price above both SMA and EMA. Volume increasing. Technical setup is bullish.",
  "agents_used": ["DataEnrichmentAgent", "AdaptiveLearningAgent", "EnsembleAI"],
  "processing_time": 8.24,
  "timestamp": "2024-03-01T10:30:00",
  "recommendation": "BUY with high confidence"
}
```

---

## Decision Meanings

| Decision | Confidence Range | Meaning |
|----------|------------------|---------|
| **accept** | > 0.75 | High confidence prediction, good buy/sell signal |
| **caution** | 0.6 - 0.75 | Moderate confidence, use with other indicators |
| **reject** | < 0.6 | Low confidence, skip this prediction |

---

## Troubleshooting

### Issue: "GEMINI_API_KEY environment variable not set"
**Solution:** 
```bash
# Check if .env file exists
ls -la .env

# Edit it with your key
nano .env
```

### Issue: "Failed to parse Gemini JSON response"
**Solution:**
- Check internet connection
- Verify API key is valid at: https://aistudio.google.com/app/apikey
- Increase GEMINI_MAX_OUTPUT_TOKENS in .env (e.g., 2048)

### Issue: Predictions are slow (> 15 seconds)
**Solution:**
- Check internet speed
- Reduce GEMINI_MAX_OUTPUT_TOKENS to 512
- Run fewer stocks in parallel

### Issue: "All retries exhausted"
**Solution:**
- Check Google's API status: https://status.cloud.google.com
- Verify API key has access to Generative AI
- Wait 5 minutes and retry

---

## Configuration Tips

### For Faster Predictions (but less detailed)
```bash
GEMINI_TEMPERATURE=0.5
GEMINI_MAX_OUTPUT_TOKENS=512
GEMINI_TOP_K=20
```

### For More Detailed Analysis (but slower)
```bash
GEMINI_TEMPERATURE=0.9
GEMINI_MAX_OUTPUT_TOKENS=2048
GEMINI_TOP_K=40
```

### For Cost Optimization
```bash
# Reduce API calls by increasing cache time
# (would need code modification)
```

---

## Monitoring Predictions

### View Logs
```bash
# On macOS/Linux
tail -f logs/stocksense.log

# Filter for Gemini calls
tail -f logs/stocksense.log | grep Gemini
```

### Check Worker Status
```bash
# Visit admin dashboard
http://localhost:5005/admin

# Check "Background Worker" section
# Shows: Downloads, Predictions, Status
```

### Database Queries
```bash
# View latest predictions
sqlite3 app/db/stock_predictions.db << EOF
SELECT company_name, predicted_price, confidence, decision 
FROM predictions 
ORDER BY prediction_date DESC 
LIMIT 10;
EOF
```

---

## API Response Times

| Component | Time |
|-----------|------|
| Data Download | 2-3s |
| Feature Engineering | 1s |
| Gemini API Call | 3-5s |
| Data Processing | 1-2s |
| Database Save | <1s |
| **Total** | **7-10s** |

---

## Common Questions

**Q: Is this better than the Keras model?**
A: Yes! Gemini has seen more financial data and updates automatically. No retraining needed.

**Q: Can I run predictions for all stocks at once?**
A: Yes, but use the background worker with limited concurrency (5 stocks at a time).

**Q: Does it cost money?**
A: Gemini API is free for moderate usage. Check pricing at: https://ai.google.dev/pricing

**Q: Can I customize the prompts?**
A: Yes! Edit `FEATURE_ANALYSIS_PROMPT` in `app/config/gemini_config.py`

**Q: How accurate are the predictions?**
A: ~65-75% accuracy (similar to traditional ML models). Use as one signal among many.

---

## Next Steps

1. ✅ Set up the API key
2. ✅ Install dependencies
3. ✅ Start the app
4. 📊 Add stocks to watchlist
5. 🤖 Enable background worker for automated predictions
6. 📈 Monitor prediction accuracy in dashboard

---

## Support

For detailed documentation, see: **GEMINI_INTEGRATION.md**

For issues:
1. Check logs: `tail -f logs/stocksense.log`
2. Verify .env configuration
3. Test API key: `curl https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key=YOUR_KEY`

