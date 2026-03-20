#!/usr/bin/env python
"""
Example script demonstrating how to use the agentic prediction system.

This script shows:
1. Basic prediction with the agentic system
2. Using adaptive learning with feedback
3. Getting performance reports
4. Adjusting confidence thresholds
"""

import logging
from datetime import datetime
from app.agents import PredictionCoordinator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_basic_prediction():
    """Example 1: Basic prediction with the agentic system"""
    print("\n" + "="*80)
    print("Example 1: Basic Agentic Prediction")
    print("="*80 + "\n")
    
    # Initialize the coordinator
    coordinator = PredictionCoordinator(min_confidence=0.6)
    
    # Make a prediction
    symbol = "AAPL"
    result = coordinator.predict(symbol, validate=True)
    
    # Display results
    print(f"Stock: {result['symbol']}")
    print(f"Predicted Price: ${result['prediction']:.2f}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Decision: {result['decision']}")
    print(f"Market Regime: {result['market_regime']}")
    print(f"\nPrediction Interval: ${result['prediction_interval'][0]:.2f} - ${result['prediction_interval'][1]:.2f}")
    print(f"Uncertainty: {result['uncertainty']:.2f}")
    print(f"\nRecommendation: {result['recommendation']}")
    
    return coordinator, result


def example_adaptive_learning(coordinator, previous_result):
    """Example 2: Adaptive learning with feedback"""
    print("\n" + "="*80)
    print("Example 2: Adaptive Learning with Feedback")
    print("="*80 + "\n")
    
    # Simulate getting actual price later
    # In real usage, this would be the actual market price the next day
    predicted_price = previous_result['prediction']
    
    # Simulate actual price (for demonstration, let's say it was close)
    actual_price = predicted_price * 1.02  # 2% higher than predicted
    
    print(f"Predicted: ${predicted_price:.2f}")
    print(f"Actual: ${actual_price:.2f}")
    print(f"Error: {abs(actual_price - predicted_price) / actual_price:.2%}")
    
    # Update the system with feedback
    coordinator.update_with_actual(
        symbol=previous_result['symbol'],
        predicted=predicted_price,
        actual=actual_price
    )
    
    print("\n✓ System updated with actual results")
    print("  The adaptive learning agent has learned from this prediction")
    print("  and will adjust future predictions accordingly.")


def example_performance_report(coordinator):
    """Example 3: Getting performance reports"""
    print("\n" + "="*80)
    print("Example 3: Performance Report")
    print("="*80 + "\n")
    
    report = coordinator.get_performance_report()
    
    print("Overall Metrics:")
    print(f"  Total Predictions: {report['metrics']['total_predictions']}")
    print(f"  High Confidence Predictions: {report['metrics']['high_confidence_predictions']}")
    print(f"  Validated Predictions: {report['metrics']['validated_predictions']}")
    print(f"  Average Confidence: {report['metrics']['average_confidence']:.2%}")
    
    print("\nAgent Performance:")
    for agent_name, perf in report['agent_performance'].items():
        print(f"\n  {agent_name}:")
        print(f"    Accuracy: {perf.get('accuracy', 0):.2%}")
        print(f"    Predictions Made: {perf.get('predictions_made', 0)}")
        
        if 'learning_report' in perf:
            print(f"    Adaptive Learning:")
            lr = perf['learning_report']
            for model, stats in lr.get('model_performance', {}).items():
                print(f"      {model}: weight={stats['weight']:.2%}, avg_error={stats.get('avg_error', 0):.2%}")


def example_multiple_predictions(coordinator):
    """Example 4: Multiple predictions and comparison"""
    print("\n" + "="*80)
    print("Example 4: Multiple Stock Predictions")
    print("="*80 + "\n")
    
    symbols = ["AAPL", "MSFT", "GOOGL"]
    
    results = []
    for symbol in symbols:
        try:
            result = coordinator.predict(symbol, validate=True)
            results.append(result)
            
            print(f"\n{symbol}:")
            print(f"  Prediction: ${result['prediction']:.2f}")
            print(f"  Confidence: {result['confidence']:.2%}")
            print(f"  Decision: {result['decision']}")
            print(f"  Market Regime: {result['market_regime']}")
        except Exception as e:
            print(f"\n{symbol}: Error - {str(e)}")
    
    # Sort by confidence
    if results:
        print("\n" + "-"*80)
        print("Ranked by Confidence:")
        print("-"*80)
        sorted_results = sorted(results, key=lambda x: x['confidence'], reverse=True)
        for i, r in enumerate(sorted_results, 1):
            print(f"{i}. {r['symbol']}: {r['confidence']:.2%} ({r['decision']})")


def example_confidence_threshold():
    """Example 5: Using different confidence thresholds"""
    print("\n" + "="*80)
    print("Example 5: Adjusting Confidence Threshold")
    print("="*80 + "\n")
    
    # Conservative approach (higher threshold)
    coordinator_conservative = PredictionCoordinator(min_confidence=0.75)
    
    # Aggressive approach (lower threshold)
    coordinator_aggressive = PredictionCoordinator(min_confidence=0.50)
    
    symbol = "AAPL"
    
    try:
        result_conservative = coordinator_conservative.predict(symbol)
        result_aggressive = coordinator_aggressive.predict(symbol)
        
        print(f"Conservative (75% threshold):")
        print(f"  Decision: {result_conservative['decision']}")
        print(f"  Confidence: {result_conservative['confidence']:.2%}")
        
        print(f"\nAggressive (50% threshold):")
        print(f"  Decision: {result_aggressive['decision']}")
        print(f"  Confidence: {result_aggressive['confidence']:.2%}")
        
        print("\nNote: Same prediction, different decision thresholds")
    except Exception as e:
        print(f"Error: {str(e)}")


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("AGENTIC PREDICTION SYSTEM - USAGE EXAMPLES")
    print("="*80)
    
    try:
        # Example 1: Basic prediction
        coordinator, result = example_basic_prediction()
        
        # Example 2: Adaptive learning
        example_adaptive_learning(coordinator, result)
        
        # Example 3: Performance report
        example_performance_report(coordinator)
        
        # Example 4: Multiple predictions
        example_multiple_predictions(coordinator)
        
        # Example 5: Confidence threshold
        example_confidence_threshold()
        
        print("\n" + "="*80)
        print("All examples completed successfully!")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Example failed: {str(e)}", exc_info=True)
        print(f"\nNote: Examples may fail in environments without internet access.")
        print(f"In production with real data access, the system will work as demonstrated.")


if __name__ == "__main__":
    main()
