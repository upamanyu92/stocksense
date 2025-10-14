"""
Prediction coordinator that orchestrates multiple agents for optimal predictions.
"""
import numpy as np
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.agents.ensemble_agent import EnsembleAgent
from app.agents.data_enrichment_agent import DataEnrichmentAgent
from app.agents.adaptive_learning_agent import AdaptiveLearningAgent


class PredictionCoordinator:
    """
    Coordinates multiple agents to make autonomous, high-accuracy predictions.
    
    This coordinator implements an agentic system that:
    1. Enriches data through data enrichment agent
    2. Makes ensemble predictions
    3. Validates predictions with confidence scoring
    4. Applies adaptive learning based on performance
    """
    
    def __init__(self, min_confidence: float = 0.6):
        """
        Initialize prediction coordinator.
        
        Args:
            min_confidence: Minimum confidence threshold for accepting predictions
        """
        self.logger = logging.getLogger("PredictionCoordinator")
        self.min_confidence = min_confidence
        
        # Initialize agents
        self.data_agent = DataEnrichmentAgent()
        self.ensemble_agent = EnsembleAgent()
        self.adaptive_agent = AdaptiveLearningAgent()
        
        # Load previous learning state if exists
        self.adaptive_agent.load_learning_state()
        
        # Decision history for adaptive learning
        self.decision_history = []
        
        # Performance tracking
        self.performance_metrics = {
            'total_predictions': 0,
            'high_confidence_predictions': 0,
            'validated_predictions': 0,
            'average_confidence': 0.0
        }
    
    def predict(self, symbol: str, validate: bool = True) -> Dict[str, Any]:
        """
        Make an autonomous prediction using the agent system.
        
        Args:
            symbol: Stock symbol to predict
            validate: Whether to perform validation checks
            
        Returns:
            Comprehensive prediction with confidence, agents used, and metadata
        """
        start_time = datetime.now()
        
        self.logger.info(f"Starting agentic prediction for {symbol}")
        
        # Step 1: Data enrichment
        self.logger.info("Step 1: Data enrichment")
        data_result = self.data_agent.predict(symbol)
        enriched_data = data_result['enriched_data']
        data_quality = data_result['quality_score']
        
        self.logger.info(f"Data quality score: {data_quality:.2f}")
        
        # Step 2: Adaptive learning strategy
        self.logger.info("Step 2: Adaptive learning strategy")
        adaptive_result = self.adaptive_agent.predict(symbol, enriched_data)
        market_regime = adaptive_result['market_regime']
        adaptive_weights = adaptive_result['adaptive_weights']
        confidence_adjustment = adaptive_result['confidence_adjustment']
        
        self.logger.info(f"Market regime: {market_regime}, Adaptive weights: {adaptive_weights}")
        
        # Step 3: Ensemble prediction with adaptive weights
        self.logger.info("Step 3: Ensemble prediction with adaptive weights")
        
        # Apply adaptive weights to ensemble
        if hasattr(self.ensemble_agent, 'model_weights'):
            self.ensemble_agent.model_weights = adaptive_weights
        
        ensemble_result = self.ensemble_agent.predict(symbol, enriched_data)
        
        prediction = ensemble_result['prediction']
        base_confidence = ensemble_result['confidence']
        
        # Apply adaptive confidence adjustment
        confidence = min(1.0, max(0.0, base_confidence + confidence_adjustment))
        
        prediction_interval = ensemble_result['prediction_interval']
        uncertainty = ensemble_result['uncertainty']
        
        self.logger.info(f"Prediction: {prediction:.2f}, Confidence: {confidence:.2f} (adjusted from {base_confidence:.2f})")
        
        # Step 4: Validation and decision making
        decision = self._make_decision(
            prediction=prediction,
            confidence=confidence,
            data_quality=data_quality,
            uncertainty=uncertainty,
            validate=validate
        )
        
        # Step 5: Compile comprehensive result
        result = {
            'symbol': symbol,
            'prediction': prediction,
            'confidence': confidence,
            'base_confidence': base_confidence,
            'confidence_adjustment': confidence_adjustment,
            'prediction_interval': prediction_interval,
            'uncertainty': uncertainty,
            'data_quality': data_quality,
            'market_regime': market_regime,
            'adaptive_weights': adaptive_weights,
            'decision': decision,
            'agents_used': [
                self.data_agent.name,
                self.adaptive_agent.name,
                self.ensemble_agent.name
            ],
            'model_details': ensemble_result.get('model_details', []),
            'processing_time': (datetime.now() - start_time).total_seconds(),
            'timestamp': datetime.now().isoformat(),
            'recommendation': self._generate_recommendation(decision, confidence, uncertainty)
        }
        
        # Update performance tracking
        self._update_performance(result)
        
        # Log decision for transparency
        self._log_decision_record(result)
        
        return result
    
    def _make_decision(
        self,
        prediction: float,
        confidence: float,
        data_quality: float,
        uncertainty: float,
        validate: bool
    ) -> str:
        """
        Make autonomous decision about the prediction quality.
        
        Args:
            prediction: The predicted value
            confidence: Model confidence
            data_quality: Quality of input data
            uncertainty: Prediction uncertainty
            validate: Whether to validate
            
        Returns:
            Decision string: 'accept', 'caution', or 'reject'
        """
        # Calculate overall trust score
        trust_score = self._calculate_trust_score(
            confidence, data_quality, uncertainty
        )
        
        self.logger.info(f"Trust score: {trust_score:.2f}")
        
        # Decision logic
        if trust_score >= 0.75:
            decision = 'accept'
        elif trust_score >= self.min_confidence:
            decision = 'caution'
        else:
            decision = 'reject'
        
        # Additional validation if requested
        if validate and decision != 'reject':
            validation_result = self._validate_prediction(prediction, confidence)
            if not validation_result:
                decision = 'caution' if decision == 'accept' else 'reject'
        
        return decision
    
    def _calculate_trust_score(
        self,
        confidence: float,
        data_quality: float,
        uncertainty: float
    ) -> float:
        """
        Calculate overall trust score from multiple factors.
        
        Args:
            confidence: Model confidence
            data_quality: Data quality score
            uncertainty: Prediction uncertainty
            
        Returns:
            Trust score between 0 and 1
        """
        # Weighted combination
        confidence_weight = 0.5
        data_quality_weight = 0.3
        uncertainty_weight = 0.2
        
        # Normalize uncertainty (lower is better)
        normalized_uncertainty = 1.0 / (1.0 + uncertainty)
        
        trust_score = (
            confidence * confidence_weight +
            data_quality * data_quality_weight +
            normalized_uncertainty * uncertainty_weight
        )
        
        return min(1.0, max(0.0, trust_score))
    
    def _validate_prediction(self, prediction: float, confidence: float) -> bool:
        """
        Validate prediction using sanity checks.
        
        Args:
            prediction: Predicted value
            confidence: Prediction confidence
            
        Returns:
            True if prediction passes validation
        """
        # Check for reasonable values
        if prediction <= 0:
            self.logger.warning("Prediction is non-positive")
            return False
        
        if np.isnan(prediction) or np.isinf(prediction):
            self.logger.warning("Prediction is NaN or Inf")
            return False
        
        # Check if prediction is within reasonable bounds
        # (e.g., stock price shouldn't jump more than 50% in a day)
        if confidence < 0.5:
            self.logger.warning("Confidence too low for validation")
            return False
        
        return True
    
    def _generate_recommendation(
        self,
        decision: str,
        confidence: float,
        uncertainty: float
    ) -> str:
        """Generate human-readable recommendation"""
        if decision == 'accept':
            return f"High confidence prediction (confidence: {confidence:.2f}). Recommended for use."
        elif decision == 'caution':
            return f"Moderate confidence prediction (confidence: {confidence:.2f}, uncertainty: {uncertainty:.2f}). Use with caution."
        else:
            return f"Low confidence prediction. Not recommended for use. Consider waiting for more data."
    
    def _update_performance(self, result: Dict[str, Any]):
        """Update performance metrics"""
        self.performance_metrics['total_predictions'] += 1
        
        if result['decision'] == 'accept':
            self.performance_metrics['high_confidence_predictions'] += 1
        
        if result['decision'] != 'reject':
            self.performance_metrics['validated_predictions'] += 1
        
        # Update running average of confidence
        n = self.performance_metrics['total_predictions']
        old_avg = self.performance_metrics['average_confidence']
        new_conf = result['confidence']
        self.performance_metrics['average_confidence'] = (
            (old_avg * (n - 1) + new_conf) / n
        )
    
    def _log_decision_record(self, result: Dict[str, Any]):
        """Log decision for audit and learning"""
        record = {
            'timestamp': result['timestamp'],
            'symbol': result['symbol'],
            'prediction': result['prediction'],
            'confidence': result['confidence'],
            'decision': result['decision'],
            'recommendation': result['recommendation']
        }
        
        self.decision_history.append(record)
        
        # Keep only recent history (last 1000 decisions)
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-1000:]
        
        self.logger.info(f"Decision recorded: {record}")
    
    def update_with_actual(self, symbol: str, predicted: float, actual: float):
        """
        Update agents with actual results for adaptive learning.
        
        Args:
            symbol: Stock symbol
            predicted: Predicted value
            actual: Actual value
        """
        # Update ensemble agent performance
        self.ensemble_agent.update_performance(actual, predicted)
        
        # Update adaptive learning agent
        for model_type in ['transformer', 'lstm']:
            self.adaptive_agent.learn_from_error(model_type, predicted, actual)
        
        # Update strategy performance if we have regime info
        if self.decision_history:
            last_decision = self.decision_history[-1]
            if last_decision.get('symbol') == symbol:
                market_regime = last_decision.get('market_regime', 'sideways')
                self.adaptive_agent.update_strategy_performance(
                    market_regime, predicted, actual
                )
        
        # Save adaptive learning state periodically
        if self.performance_metrics['total_predictions'] % 10 == 0:
            self.adaptive_agent.save_learning_state()
        
        # Adaptive learning: adjust ensemble method based on performance
        error_rate = abs(actual - predicted) / actual
        
        if error_rate > 0.10:  # More than 10% error
            self.logger.info(f"High error rate detected for {symbol}: {error_rate:.2%}")
            self.logger.info("Consider model retraining")
            
            # Could trigger automatic retraining here
            # from app.models.model_monitor import ModelPerformanceMonitor
            # ModelPerformanceMonitor.monitor_and_retrain()
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        return {
            'metrics': self.performance_metrics,
            'agent_performance': {
                'data_enrichment_agent': {
                    'accuracy': self.data_agent.get_accuracy(),
                    'predictions_made': self.data_agent.metadata['predictions_made']
                },
                'ensemble_agent': {
                    'accuracy': self.ensemble_agent.get_accuracy(),
                    'predictions_made': self.ensemble_agent.metadata['predictions_made']
                },
                'adaptive_learning_agent': {
                    'accuracy': self.adaptive_agent.get_accuracy(),
                    'learning_report': self.adaptive_agent.get_learning_report()
                }
            },
            'recent_decisions': self.decision_history[-10:] if self.decision_history else []
        }
    
    def set_confidence_threshold(self, threshold: float):
        """Update minimum confidence threshold"""
        if 0.0 <= threshold <= 1.0:
            self.min_confidence = threshold
            self.logger.info(f"Confidence threshold updated to {threshold}")
        else:
            raise ValueError("Threshold must be between 0 and 1")
