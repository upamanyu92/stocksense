# Agentic Prediction System for Stock Sense

## Overview

This document describes the enhanced agentic prediction system implemented to improve prediction accuracy and make the prediction process more autonomous and intelligent.

## Key Improvements

### 1. **Agentic Architecture**

The system now uses a multi-agent architecture where specialized agents work together to make autonomous decisions:

- **Data Enrichment Agent**: Enriches stock data with advanced technical indicators and features
- **Ensemble Agent**: Combines predictions from multiple models (Transformer + LSTM) for improved accuracy
- **Adaptive Learning Agent**: Learns from prediction errors and adapts strategies based on market conditions
- **Prediction Coordinator**: Orchestrates all agents and makes final decisions

### 2. **Enhanced Features for Better Accuracy**

#### Advanced Technical Indicators
- Fibonacci retracement levels
- Support and resistance levels
- Market regime detection (bull/bear/sideways/volatile)
- Volatility clustering features
- Momentum indicators at multiple timeframes
- ADX for trend strength
- Stochastic oscillators

#### Market Regime Awareness
The system automatically detects market conditions and adapts:
- **Bull Market**: Prefers Transformer model, +10% confidence boost
- **Bear Market**: Prefers LSTM model, +5% confidence boost
- **Sideways Market**: Uses balanced ensemble
- **Volatile Market**: Uses ensemble with -10% confidence penalty

### 3. **Ensemble Prediction**

Multiple ensemble methods available:
- **Weighted Average**: Weights predictions by model confidence
- **Simple Average**: Equal weight to all models
- **Voting/Median**: Robust to outliers

### 4. **Adaptive Learning**

The system continuously improves through:
- **Online Learning**: Updates model weights based on prediction errors
- **Performance Tracking**: Monitors each model's accuracy over time
- **Automatic Weight Adjustment**: Increases weight for better-performing models
- **Strategy Adaptation**: Adjusts confidence boosts based on regime-specific performance
- **Persistent Learning State**: Saves and loads learning progress

### 5. **Confidence Scoring & Uncertainty Quantification**

Every prediction includes:
- **Base Confidence**: From ensemble model agreement
- **Adjusted Confidence**: Includes data quality and market regime factors
- **Prediction Interval**: 95% confidence interval based on model variance
- **Uncertainty Score**: Standard deviation of model predictions
- **Trust Score**: Combined metric of confidence, data quality, and uncertainty

### 6. **Autonomous Decision Making**

The coordinator makes intelligent decisions:
- **Accept**: High confidence (>75% trust score) - Recommended for use
- **Caution**: Moderate confidence (60-75% trust score) - Use with care
- **Reject**: Low confidence (<60% trust score) - Not recommended

### 7. **Data Quality Assessment**

Evaluates input data on:
- Missing value ratio
- Data recency (penalizes stale data)
- Data volume (prefers more historical data)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Prediction Coordinator                     │
│  (Orchestrates all agents and makes final decisions)        │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│Data Enrich   │    │Adaptive      │    │Ensemble      │
│Agent         │───▶│Learning      │───▶│Agent         │
│              │    │Agent         │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        │                   │                   │
        ▼                   ▼                   ▼
   Enhanced            Market Regime      Transformer
   Features            & Weights          + LSTM Models
```

## Usage

### Basic Usage

```python
from app.agents import PredictionCoordinator

# Initialize coordinator
coordinator = PredictionCoordinator(min_confidence=0.6)

# Make prediction
result = coordinator.predict('AAPL', validate=True)

print(f"Prediction: ${result['prediction']:.2f}")
print(f"Confidence: {result['confidence']:.2%}")
print(f"Decision: {result['decision']}")
print(f"Recommendation: {result['recommendation']}")
```

### Advanced Usage with Feedback

```python
# Make prediction
result = coordinator.predict('AAPL')

# Later, when actual price is known
actual_price = 150.25
coordinator.update_with_actual(
    symbol='AAPL',
    predicted=result['prediction'],
    actual=actual_price
)

# System learns and adapts weights automatically
```

### Performance Monitoring

```python
# Get comprehensive performance report
report = coordinator.get_performance_report()

print(f"Total Predictions: {report['metrics']['total_predictions']}")
print(f"Average Confidence: {report['metrics']['average_confidence']:.2%}")

# View agent performance
for agent_name, perf in report['agent_performance'].items():
    print(f"{agent_name}: {perf['accuracy']:.2%} accuracy")
```

## Integration with Existing System

The agentic system is integrated into the existing `prediction_service.py`:

```python
from app.agents.prediction_coordinator import PredictionCoordinator

# Initialize once
prediction_coordinator = PredictionCoordinator(min_confidence=0.6)

# Use in prediction executor
result = prediction_coordinator.predict(stock_symbol_yahoo, validate=True)
predicted_price = result['prediction']
confidence = result['confidence']
decision = result['decision']

# Fallback to traditional method if rejected
if decision == 'reject':
    predicted_price = predict_max_profit(stock_symbol_yahoo)
```

## Path to 100% Accuracy

While 100% prediction accuracy is theoretically impossible in stock markets due to inherent randomness and efficient market hypothesis, this system approaches maximum achievable accuracy through:

1. **Ensemble Diversity**: Combining multiple models reduces bias
2. **Adaptive Learning**: Continuous improvement from feedback
3. **Market Awareness**: Different strategies for different conditions
4. **Quality Control**: Only accepting high-confidence predictions
5. **Uncertainty Quantification**: Being honest about prediction limits
6. **Feature Richness**: Using comprehensive technical indicators
7. **Data Quality Checks**: Ensuring input data reliability

## Performance Metrics

The system tracks and optimizes for:
- **MAPE** (Mean Absolute Percentage Error)
- **Directional Accuracy** (Predicted up/down correctly)
- **Confidence Calibration** (Confidence matches actual accuracy)
- **Trust Score** (Overall prediction reliability)

## Future Enhancements

Potential improvements for even better accuracy:
1. Add sentiment analysis from news/social media
2. Incorporate fundamental analysis data
3. Use reinforcement learning for strategy selection
4. Add cross-asset correlation features
5. Implement ensemble pruning based on performance
6. Add explainability features (SHAP values)
7. Implement online model retraining

## Files Added

- `app/agents/__init__.py` - Agent module initialization
- `app/agents/base_agent.py` - Base class for all agents
- `app/agents/ensemble_agent.py` - Ensemble prediction agent
- `app/agents/data_enrichment_agent.py` - Data enrichment agent
- `app/agents/adaptive_learning_agent.py` - Adaptive learning agent
- `app/agents/prediction_coordinator.py` - Main coordinator

## Files Modified

- `app/services/prediction_service.py` - Integrated agentic system
- `app/features/feature_factory.py` - Already had rich features

## Benefits

1. **Higher Accuracy**: Ensemble + adaptive learning improves predictions
2. **Autonomous**: Makes intelligent decisions without human intervention
3. **Transparent**: Logs all decisions with reasoning
4. **Self-Improving**: Learns from errors and adapts
5. **Robust**: Falls back gracefully when confidence is low
6. **Comprehensive**: Provides full context with every prediction

## Conclusion

This agentic system transforms StockSense from a simple prediction tool into an intelligent, self-improving prediction platform that approaches maximum achievable accuracy through multi-agent collaboration, continuous learning, and intelligent decision-making.
