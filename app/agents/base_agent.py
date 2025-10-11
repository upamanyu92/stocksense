"""
Base agent class for the agentic prediction system.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from datetime import datetime


class BaseAgent(ABC):
    """Base class for all prediction agents"""
    
    def __init__(self, name: str, confidence_threshold: float = 0.7):
        """
        Initialize base agent.
        
        Args:
            name: Agent name
            confidence_threshold: Minimum confidence level for predictions
        """
        self.name = name
        self.confidence_threshold = confidence_threshold
        self.logger = logging.getLogger(f"Agent.{name}")
        self.metadata = {
            'created_at': datetime.now(),
            'predictions_made': 0,
            'successful_predictions': 0
        }
    
    @abstractmethod
    def predict(self, symbol: str, data: Any) -> Dict[str, Any]:
        """
        Make a prediction for the given symbol.
        
        Args:
            symbol: Stock symbol
            data: Input data for prediction
            
        Returns:
            Dictionary containing prediction, confidence, and metadata
        """
        pass
    
    @abstractmethod
    def get_confidence(self, prediction: Any, data: Any) -> float:
        """
        Calculate confidence score for the prediction.
        
        Args:
            prediction: The prediction made
            data: Input data used for prediction
            
        Returns:
            Confidence score between 0 and 1
        """
        pass
    
    def update_performance(self, actual: float, predicted: float):
        """
        Update agent performance metrics.
        
        Args:
            actual: Actual value
            predicted: Predicted value
        """
        self.metadata['predictions_made'] += 1
        
        # Consider prediction successful if within 5% error
        error_rate = abs(actual - predicted) / actual
        if error_rate <= 0.05:
            self.metadata['successful_predictions'] += 1
    
    def get_accuracy(self) -> float:
        """Get current prediction accuracy"""
        if self.metadata['predictions_made'] == 0:
            return 0.0
        return self.metadata['successful_predictions'] / self.metadata['predictions_made']
    
    def log_decision(self, decision: str, details: Dict[str, Any]):
        """
        Log agent decision for transparency.
        
        Args:
            decision: Decision description
            details: Additional decision details
        """
        self.logger.info(f"Agent {self.name}: {decision}")
        self.logger.debug(f"Details: {details}")
