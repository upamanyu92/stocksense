"""
Adaptive learning agent that continuously improves predictions based on feedback.
"""
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
import logging
from datetime import datetime, timedelta
from pathlib import Path
import json

from app.agents.base_agent import BaseAgent


class AdaptiveLearningAgent(BaseAgent):
    """
    Agent that learns from prediction errors and adapts strategies for improved accuracy.
    
    This agent implements:
    1. Online learning from prediction errors
    2. Strategy selection based on market conditions
    3. Performance-based model weighting
    4. Automatic hyperparameter tuning
    """
    
    def __init__(self, name: str = "AdaptiveLearningAgent", confidence_threshold: float = 0.7):
        super().__init__(name, confidence_threshold)
        
        # Learning parameters
        self.learning_rate = 0.1
        self.decay_rate = 0.95
        
        # Model performance tracking
        self.model_performance = {
            'transformer': {'errors': [], 'weights': 1.0},
            'lstm': {'errors': [], 'weights': 1.0}
        }
        
        # Market regime detection
        self.market_regimes = ['bull', 'bear', 'sideways', 'volatile']
        self.regime_strategies = {
            'bull': {'model_preference': 'transformer', 'confidence_boost': 0.1},
            'bear': {'model_preference': 'lstm', 'confidence_boost': 0.05},
            'sideways': {'model_preference': 'ensemble', 'confidence_boost': 0.0},
            'volatile': {'model_preference': 'ensemble', 'confidence_boost': -0.1}
        }
        
        # Prediction history for learning
        self.prediction_history = []
        self.max_history = 1000
        
        # Adaptive weights for ensemble
        self.adaptive_weights = {'transformer': 0.5, 'lstm': 0.5}
    
    def predict(self, symbol: str, data: Any = None) -> Dict[str, Any]:
        """
        Make adaptive prediction with learned strategies.
        
        Args:
            symbol: Stock symbol
            data: Optional data
            
        Returns:
            Adaptive prediction with recommended strategy
        """
        # Detect current market regime
        market_regime = self._detect_market_regime(data) if data is not None else 'sideways'
        
        # Get strategy for current regime
        strategy = self.regime_strategies.get(market_regime, self.regime_strategies['sideways'])
        
        # Calculate adaptive model weights
        adaptive_weights = self._calculate_adaptive_weights()
        
        result = {
            'market_regime': market_regime,
            'recommended_strategy': strategy,
            'adaptive_weights': adaptive_weights,
            'confidence_adjustment': strategy['confidence_boost']
        }
        
        self.log_decision(
            f"Adaptive strategy selected for {market_regime} market",
            result
        )
        
        return result
    
    def learn_from_error(self, model_type: str, predicted: float, actual: float):
        """
        Learn from prediction error and update model weights.
        
        Args:
            model_type: Type of model that made the prediction
            predicted: Predicted value
            actual: Actual value
        """
        if model_type not in self.model_performance:
            return
        
        # Calculate error
        error = abs(actual - predicted) / actual
        
        # Store error
        self.model_performance[model_type]['errors'].append(error)
        
        # Keep only recent errors
        if len(self.model_performance[model_type]['errors']) > 100:
            self.model_performance[model_type]['errors'] = \
                self.model_performance[model_type]['errors'][-100:]
        
        # Update model weight based on performance
        recent_errors = self.model_performance[model_type]['errors'][-20:]
        avg_error = np.mean(recent_errors)
        
        # Lower error = higher weight
        new_weight = 1.0 / (1.0 + avg_error)
        
        # Apply exponential moving average for smooth updates
        old_weight = self.model_performance[model_type]['weights']
        self.model_performance[model_type]['weights'] = (
            self.learning_rate * new_weight + 
            (1 - self.learning_rate) * old_weight
        )
        
        self.log_decision(
            f"Weight updated for {model_type}",
            {
                'error': error,
                'avg_error': avg_error,
                'new_weight': self.model_performance[model_type]['weights']
            }
        )
    
    def _calculate_adaptive_weights(self) -> Dict[str, float]:
        """
        Calculate adaptive weights for ensemble based on recent performance.
        
        Returns:
            Dictionary of normalized model weights
        """
        weights = {}
        total_weight = 0
        
        for model_type, perf_data in self.model_performance.items():
            weights[model_type] = perf_data['weights']
            total_weight += perf_data['weights']
        
        # Normalize weights
        if total_weight > 0:
            for model_type in weights:
                weights[model_type] /= total_weight
        
        return weights
    
    def _detect_market_regime(self, data: Any) -> str:
        """
        Detect current market regime from data.
        
        Args:
            data: Market data
            
        Returns:
            Market regime string
        """
        import pandas as pd
        
        if not isinstance(data, pd.DataFrame):
            return 'sideways'
        
        if len(data) < 50:
            return 'sideways'
        
        # Calculate regime indicators
        recent_data = data.tail(50)
        
        # Trend detection
        sma_20 = recent_data['Close'].rolling(20).mean().iloc[-1]
        sma_50 = recent_data['Close'].rolling(50).mean().iloc[-1]
        current_price = recent_data['Close'].iloc[-1]
        
        # Volatility detection
        volatility = recent_data['Close'].pct_change().std()
        
        # Determine regime
        if volatility > 0.03:  # High volatility
            return 'volatile'
        elif current_price > sma_20 > sma_50:  # Uptrend
            return 'bull'
        elif current_price < sma_20 < sma_50:  # Downtrend
            return 'bear'
        else:
            return 'sideways'
    
    def update_strategy_performance(
        self,
        regime: str,
        predicted: float,
        actual: float
    ):
        """
        Update strategy performance for a specific market regime.
        
        Args:
            regime: Market regime
            predicted: Predicted value
            actual: Actual value
        """
        if regime not in self.regime_strategies:
            return
        
        error = abs(actual - predicted) / actual
        
        # Adjust confidence boost based on performance
        if error < 0.05:  # Good prediction
            self.regime_strategies[regime]['confidence_boost'] += 0.01
        elif error > 0.15:  # Poor prediction
            self.regime_strategies[regime]['confidence_boost'] -= 0.01
        
        # Keep confidence boost in reasonable range
        self.regime_strategies[regime]['confidence_boost'] = np.clip(
            self.regime_strategies[regime]['confidence_boost'],
            -0.2, 0.2
        )
        
        self.log_decision(
            f"Strategy performance updated for {regime} regime",
            {
                'error': error,
                'new_confidence_boost': self.regime_strategies[regime]['confidence_boost']
            }
        )
    
    def get_confidence(self, prediction: Any, data: Any) -> float:
        """Get confidence for adaptive predictions"""
        if isinstance(prediction, dict):
            base_confidence = 0.7
            adjustment = prediction.get('confidence_adjustment', 0.0)
            return min(1.0, max(0.0, base_confidence + adjustment))
        return 0.7
    
    def save_learning_state(self, filepath: str = "model/adaptive_learning_state.json"):
        """Save learning state for persistence"""
        state = {
            'model_performance': {
                k: {
                    'weights': v['weights'],
                    'recent_errors': v['errors'][-20:] if v['errors'] else []
                }
                for k, v in self.model_performance.items()
            },
            'regime_strategies': self.regime_strategies,
            'adaptive_weights': self.adaptive_weights,
            'metadata': self.metadata,
            'timestamp': datetime.now().isoformat()
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        
        self.logger.info(f"Learning state saved to {filepath}")
    
    def load_learning_state(self, filepath: str = "model/adaptive_learning_state.json"):
        """Load previous learning state"""
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
            
            # Restore model performance
            for model_type, perf_data in state.get('model_performance', {}).items():
                if model_type in self.model_performance:
                    self.model_performance[model_type]['weights'] = perf_data.get('weights', 1.0)
                    self.model_performance[model_type]['errors'] = perf_data.get('recent_errors', [])
            
            # Restore regime strategies
            self.regime_strategies = state.get('regime_strategies', self.regime_strategies)
            self.adaptive_weights = state.get('adaptive_weights', self.adaptive_weights)
            
            self.logger.info(f"Learning state loaded from {filepath}")
            return True
        except Exception as e:
            self.logger.warning(f"Could not load learning state: {str(e)}")
            return False
    
    def get_learning_report(self) -> Dict[str, Any]:
        """Get comprehensive learning report"""
        return {
            'model_performance': {
                model: {
                    'weight': perf['weights'],
                    'avg_error': np.mean(perf['errors']) if perf['errors'] else 0,
                    'predictions_count': len(perf['errors'])
                }
                for model, perf in self.model_performance.items()
            },
            'regime_strategies': self.regime_strategies,
            'adaptive_weights': self.adaptive_weights,
            'overall_accuracy': self.get_accuracy()
        }
