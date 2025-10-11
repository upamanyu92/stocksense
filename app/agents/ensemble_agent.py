"""
Ensemble agent that combines predictions from multiple models for improved accuracy.
"""
import numpy as np
from typing import Dict, Any, List, Tuple
import logging
from pathlib import Path

from app.agents.base_agent import BaseAgent
from app.models.keras_model import predict_max_profit, load_latest_model
from app.features.feature_factory import create_features
import yfinance as yf


class EnsembleAgent(BaseAgent):
    """Agent that uses ensemble methods to combine multiple model predictions"""
    
    def __init__(self, name: str = "EnsembleAgent", confidence_threshold: float = 0.7):
        super().__init__(name, confidence_threshold)
        self.model_types = ['transformer', 'lstm']
        self.ensemble_method = 'weighted_average'  # Can be 'average', 'weighted_average', 'voting'
        self.model_weights = {}
    
    def predict(self, symbol: str, data: Any = None) -> Dict[str, Any]:
        """
        Make ensemble prediction by combining multiple models.
        
        Args:
            symbol: Stock symbol
            data: Optional pre-loaded data
            
        Returns:
            Dictionary with prediction, confidence, and ensemble details
        """
        predictions = []
        confidences = []
        model_details = []
        
        # Get predictions from each model type
        for model_type in self.model_types:
            try:
                use_transformer = (model_type == 'transformer')
                pred = predict_max_profit(symbol, use_transformer=use_transformer)
                
                # Calculate confidence based on model performance history
                confidence = self._get_model_confidence(symbol, model_type)
                
                predictions.append(pred)
                confidences.append(confidence)
                model_details.append({
                    'model_type': model_type,
                    'prediction': float(pred),
                    'confidence': float(confidence)
                })
                
                self.log_decision(
                    f"Prediction from {model_type}",
                    {'symbol': symbol, 'prediction': pred, 'confidence': confidence}
                )
            except Exception as e:
                self.logger.warning(f"Failed to get prediction from {model_type}: {str(e)}")
                continue
        
        if not predictions:
            raise ValueError(f"No models could make predictions for {symbol}")
        
        # Combine predictions using ensemble method
        final_prediction = self._combine_predictions(predictions, confidences)
        final_confidence = self._calculate_ensemble_confidence(confidences)
        
        # Calculate prediction interval for uncertainty quantification
        prediction_interval = self._calculate_prediction_interval(predictions)
        
        result = {
            'prediction': float(final_prediction),
            'confidence': float(final_confidence),
            'prediction_interval': prediction_interval,
            'ensemble_method': self.ensemble_method,
            'model_details': model_details,
            'num_models': len(predictions),
            'uncertainty': float(np.std(predictions))
        }
        
        self.log_decision(
            "Ensemble prediction complete",
            {'symbol': symbol, 'result': result}
        )
        
        return result
    
    def _combine_predictions(self, predictions: List[float], confidences: List[float]) -> float:
        """Combine predictions using the configured ensemble method"""
        predictions = np.array(predictions)
        confidences = np.array(confidences)
        
        if self.ensemble_method == 'average':
            return np.mean(predictions)
        
        elif self.ensemble_method == 'weighted_average':
            # Weight by confidence
            if np.sum(confidences) == 0:
                return np.mean(predictions)
            weights = confidences / np.sum(confidences)
            return np.sum(predictions * weights)
        
        elif self.ensemble_method == 'voting':
            # Use median as robust voting mechanism
            return np.median(predictions)
        
        else:
            return np.mean(predictions)
    
    def _calculate_ensemble_confidence(self, confidences: List[float]) -> float:
        """Calculate overall confidence from individual model confidences"""
        if not confidences:
            return 0.0
        
        # Use weighted average with variance penalty
        mean_conf = np.mean(confidences)
        variance_penalty = 1.0 - (np.std(confidences) / (mean_conf + 1e-6))
        
        return mean_conf * max(0.5, variance_penalty)
    
    def _calculate_prediction_interval(self, predictions: List[float]) -> Tuple[float, float]:
        """Calculate prediction interval based on model variance"""
        predictions = np.array(predictions)
        mean = np.mean(predictions)
        std = np.std(predictions)
        
        # 95% confidence interval
        lower = mean - 1.96 * std
        upper = mean + 1.96 * std
        
        return (float(lower), float(upper))
    
    def _get_model_confidence(self, symbol: str, model_type: str) -> float:
        """
        Get confidence score for a specific model based on historical performance.
        
        This could be enhanced to query actual performance metrics from database.
        """
        # Default confidence based on model type
        base_confidence = {
            'transformer': 0.75,
            'lstm': 0.70
        }
        
        # Check if model exists
        model, scaler, metadata = load_latest_model(symbol, model_type)
        if model is None:
            return 0.5  # Lower confidence for untrained models
        
        return base_confidence.get(model_type, 0.6)
    
    def get_confidence(self, prediction: Any, data: Any) -> float:
        """Get confidence for ensemble prediction"""
        if isinstance(prediction, dict):
            return prediction.get('confidence', 0.0)
        return 0.0
    
    def set_ensemble_method(self, method: str):
        """Change the ensemble method"""
        valid_methods = ['average', 'weighted_average', 'voting']
        if method not in valid_methods:
            raise ValueError(f"Invalid method. Choose from: {valid_methods}")
        self.ensemble_method = method
        self.log_decision(f"Ensemble method changed to {method}", {})
