# StockSense Examples

This directory contains example scripts demonstrating how to use the StockSense agentic prediction system.

## Available Examples

### agentic_prediction_examples.py

Comprehensive examples showing:

1. **Basic Prediction**: How to make a simple prediction using the agentic system
2. **Adaptive Learning**: How to provide feedback to improve future predictions
3. **Performance Reports**: How to monitor system performance
4. **Multiple Predictions**: How to predict multiple stocks and compare results
5. **Confidence Thresholds**: How to adjust decision-making thresholds

## Running the Examples

```bash
# From the project root
python examples/agentic_prediction_examples.py
```

Or run with PYTHONPATH:

```bash
PYTHONPATH=/path/to/stocksense python examples/agentic_prediction_examples.py
```

## Example Output

When you run the examples, you'll see output like:

```
Example 1: Basic Agentic Prediction
================================================================================

Stock: AAPL
Predicted Price: $175.50
Confidence: 78%
Decision: accept
Market Regime: bull

Prediction Interval: $173.20 - $177.80
Uncertainty: 2.30

Recommendation: High confidence prediction (confidence: 0.78). Recommended for use.
```

## Integration Example

To integrate the agentic system into your own code:

```python
from app.agents import PredictionCoordinator

# Initialize
coordinator = PredictionCoordinator(min_confidence=0.6)

# Make prediction
result = coordinator.predict('AAPL', validate=True)

# Use the prediction
if result['decision'] in ['accept', 'caution']:
    predicted_price = result['prediction']
    confidence = result['confidence']
    # Your trading logic here
else:
    # Low confidence, skip or use fallback method
    pass

# Later, provide feedback for learning
coordinator.update_with_actual('AAPL', predicted_price, actual_price)
```

## Notes

- Examples require internet access to download stock data
- In production, the system will cache data and work more efficiently
- The adaptive learning agent saves state to `model/adaptive_learning_state.json`
- All predictions are logged for audit and transparency
