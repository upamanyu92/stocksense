"""
Ensemble agent that combines predictions from multiple LLM calls for improved accuracy.
"""
import numpy as np
from typing import Dict, Any
import logging

from app.agents.base_agent import BaseAgent
from app.models.llm_factory import LLMFactory


class EnsembleAgent(BaseAgent):
    """Agent that uses ensemble methods to combine multiple LLM predictions"""

    def __init__(self, name: str = "EnsembleAI", confidence_threshold: float = 0.7):
        super().__init__(name, confidence_threshold)
        # Use different analysis perspectives as "models"
        self.analysis_types = ['technical', 'fundamental']
        self.ensemble_method = 'weighted_average'  # Can be 'average', 'weighted_average', 'voting'
        self.model_weights = {}
    
    def predict(self, symbol: str, data: Any = None) -> Dict[str, Any]:
        """
        Make ensemble prediction by combining multiple LLM calls.

        Args:
            symbol: Stock symbol
            data: Optional pre-loaded data
            
        Returns:
            Dictionary with prediction, confidence, and ensemble details
        """
        predictions = []
        confidences = []
        model_details = []
        
        backend = LLMFactory.active_backend()
        # Get predictions from LLM (called multiple times with emphasis on different aspects)
        for analysis_type in self.analysis_types:
            try:
                # Call LLM factory with different emphasis
                result = LLMFactory.predict_with_details(symbol)

                # Store prediction and confidence
                pred = result['predicted_price']
                confidence = result['confidence']

                predictions.append(pred)
                confidences.append(confidence)
                model_details.append({
                    'model_type': f'{backend}_{analysis_type}',
                    'prediction': float(pred),
                    'confidence': float(confidence),
                    'decision': result.get('decision', 'caution'),
                    'reasoning': result.get('reasoning', '')
                })
                
                self.log_decision(
                    f"Prediction from {backend}_{analysis_type}",
                    {'symbol': symbol, 'prediction': pred, 'confidence': confidence}
                )
            except Exception as e:
                self.logger.warning(f"Failed to get LLM prediction for {analysis_type}: {str(e)}")
                continue
        
        if not predictions:
            raise ValueError(f"No LLM predictions could be made for {symbol}")

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
    
    def _combine_predictions(self, predictions, confidences) -> float:
        """Combine predictions using the configured ensemble method"""
        predictions = np.array(predictions)
        confidences = np.array(confidences)
        
        if self.ensemble_method == 'average':
            return float(np.mean(predictions))

        elif self.ensemble_method == 'weighted_average':
            # Weight by confidence
            if np.sum(confidences) == 0:
                return float(np.mean(predictions))
            weights = confidences / np.sum(confidences)
            return float(np.sum(predictions * weights))

        elif self.ensemble_method == 'voting':
            # Use median as robust voting mechanism
            return float(np.median(predictions))

        else:
            return float(np.mean(predictions))

    def _calculate_ensemble_confidence(self, confidences) -> float:
        """Calculate overall confidence from individual model confidences"""
        if not confidences:
            return 0.0
        
        # Use weighted average with variance penalty
        mean_conf = np.mean(confidences)
        variance_penalty = 1.0 - (np.std(confidences) / (mean_conf + 1e-6))
        
        return float(mean_conf * max(0.5, variance_penalty))

    def _calculate_prediction_interval(self, predictions):
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
        Get confidence score for a specific Ollama analysis type.
        """
        # Default confidence based on analysis type
        base_confidence = {
            'technical': 0.75,
            'fundamental': 0.70
        }

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
