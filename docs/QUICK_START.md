# Agentic Prediction System - Quick Start Guide

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Basic Usage (3 Lines)

```python
from app.agents import PredictionCoordinator

coordinator = PredictionCoordinator()
result = coordinator.predict('AAPL')
print(f"Prediction: ${result['prediction']:.2f} (confidence: {result['confidence']:.2%})")
```

## Complete Workflow

```python
from app.agents import PredictionCoordinator

# 1. Initialize
coordinator = PredictionCoordinator(min_confidence=0.6)

# 2. Make prediction
result = coordinator.predict('AAPL', validate=True)

# 3. Check decision
if result['decision'] == 'accept':
    print(f"✓ High confidence: ${result['prediction']:.2f}")
    predicted_price = result['prediction']
elif result['decision'] == 'caution':
    print(f"⚠ Moderate confidence: ${result['prediction']:.2f}")
    predicted_price = result['prediction']
else:
    print(f"✗ Low confidence - skipping")
    predicted_price = None

# 4. Later, provide feedback (when actual price is known)
if predicted_price:
    actual_price = 177.25  # Get from market
    coordinator.update_with_actual('AAPL', predicted_price, actual_price)
```

## Using the REST API

```bash
# Make prediction
curl "http://localhost:5000/api/agentic/predict/AAPL"

# Provide feedback
curl -X POST "http://localhost:5000/api/agentic/feedback" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "predicted": 175.50, "actual": 177.25}'

# Get performance report
curl "http://localhost:5000/api/agentic/performance"
```

## Understanding Results

### Decision Values
- `accept`: High confidence (>75%) - Use this prediction
- `caution`: Moderate confidence (60-75%) - Use carefully
- `reject`: Low confidence (<60%) - Don't use

### Key Metrics
- `prediction`: Predicted price
- `confidence`: How confident the system is (0-1)
- `prediction_interval`: 95% confidence range
- `uncertainty`: Standard deviation of model predictions
- `market_regime`: bull/bear/sideways/volatile

### Example Output
```json
{
  "prediction": 175.50,
  "confidence": 0.78,
  "decision": "accept",
  "prediction_interval": [173.20, 177.80],
  "market_regime": "bull",
  "recommendation": "High confidence prediction. Recommended for use."
}
```

## Best Practices

### 1. Filter by Confidence
```python
if result['confidence'] > 0.75:
    # Use prediction
    trade_on_prediction(result)
```

### 2. Use Prediction Intervals
```python
lower, upper = result['prediction_interval']
# Consider the range, not just point estimate
```

### 3. Monitor Performance
```python
report = coordinator.get_performance_report()
print(f"Accuracy: {report['agent_performance']['ensemble_agent']['accuracy']:.2%}")
```

### 4. Provide Feedback
```python
# Always provide feedback for learning
coordinator.update_with_actual(symbol, predicted, actual)
```

### 5. Respect Market Regimes
```python
if result['market_regime'] == 'volatile':
    # Be more conservative
    risk_factor = 0.5
else:
    risk_factor = 1.0
```

## Common Patterns

### Batch Predictions
```python
symbols = ['AAPL', 'MSFT', 'GOOGL']
predictions = []

for symbol in symbols:
    try:
        result = coordinator.predict(symbol)
        if result['decision'] in ['accept', 'caution']:
            predictions.append(result)
    except Exception as e:
        print(f"Error for {symbol}: {e}")

# Sort by confidence
predictions.sort(key=lambda x: x['confidence'], reverse=True)
```

### Conservative Strategy
```python
# Higher threshold, only accept high confidence
conservative = PredictionCoordinator(min_confidence=0.75)
result = conservative.predict('AAPL')
# Will more often return 'caution' or 'reject'
```

### Aggressive Strategy
```python
# Lower threshold, accept more predictions
aggressive = PredictionCoordinator(min_confidence=0.50)
result = aggressive.predict('AAPL')
# Will more often return 'accept'
```

## Integration with Existing Code

### Replace Existing Prediction
```python
# Before:
predicted_price = predict_max_profit(symbol)

# After:
coordinator = PredictionCoordinator()
result = coordinator.predict(symbol)
predicted_price = result['prediction']
confidence = result['confidence']
```

### Add to Prediction Service
```python
from app.agents import PredictionCoordinator

# Initialize once
coordinator = PredictionCoordinator(min_confidence=0.6)

def prediction_executor(data):
    symbol = data.get('security_id')
    result = coordinator.predict(symbol, validate=True)
    
    if result['decision'] == 'reject':
        # Fallback to traditional method
        predicted_price = predict_max_profit(symbol)
    else:
        predicted_price = result['prediction']
    
    # Store prediction with confidence
    store_prediction(symbol, predicted_price, result['confidence'])
```

## Troubleshooting

### Problem: Low Confidence Predictions
**Solution**: 
- Check data quality
- Ensure sufficient historical data
- Consider market regime (volatile = lower confidence)

### Problem: Predictions Keep Getting Rejected
**Solution**:
- Lower confidence threshold: `PredictionCoordinator(min_confidence=0.5)`
- Check if data is accessible
- Verify models are trained

### Problem: Poor Accuracy
**Solution**:
- Provide feedback regularly: `update_with_actual()`
- Check performance report
- Consider retraining models
- Verify data quality

## Performance Expectations

| Condition | Directional Accuracy | MAPE |
|-----------|---------------------|------|
| High confidence (>0.75) | 85-90% | 2-3% |
| Normal (0.60-0.75) | 75-80% | 3-5% |
| Low (<0.60) | 60-70% | 5-8% |

## Next Steps

1. **Read Full Documentation**: [docs/AGENTIC_SYSTEM.md](AGENTIC_SYSTEM.md)
2. **Try Examples**: `python examples/agentic_prediction_examples.py`
3. **Review API**: [docs/API.md](API.md)
4. **Understand Accuracy**: [docs/ACCURACY_ANALYSIS.md](ACCURACY_ANALYSIS.md)

## Support

For issues or questions:
1. Check documentation in `docs/` folder
2. Review examples in `examples/` folder
3. Open an issue on GitHub

## Quick Tips

✅ **Do**:
- Use high-confidence predictions
- Provide regular feedback
- Monitor performance
- Combine with other analysis

❌ **Don't**:
- Rely solely on predictions
- Ignore confidence scores
- Skip feedback updates
- Expect 100% accuracy

---

**Remember**: This is a tool to improve decision-making, not a crystal ball. Always combine with fundamental analysis and risk management.
