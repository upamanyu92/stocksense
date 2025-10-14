"""
REST API endpoints for the agentic prediction system.

This module provides HTTP endpoints to access the agentic prediction functionality.
"""
from flask import Blueprint, request, jsonify
import logging

from app.agents import PredictionCoordinator

# Create blueprint
agentic_api = Blueprint('agentic_api', __name__, url_prefix='/api/agentic')

# Initialize coordinator (singleton)
_coordinator = None

def get_coordinator():
    """Get or create the prediction coordinator singleton"""
    global _coordinator
    if _coordinator is None:
        _coordinator = PredictionCoordinator(min_confidence=0.6)
    return _coordinator


@agentic_api.route('/predict/<symbol>', methods=['GET'])
def predict(symbol):
    """
    Make an agentic prediction for a stock symbol.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        
    Query Parameters:
        validate: Whether to validate prediction (default: true)
        min_confidence: Minimum confidence threshold (default: 0.6)
        
    Returns:
        JSON with prediction results
    """
    try:
        # Parse query parameters
        validate = request.args.get('validate', 'true').lower() == 'true'
        min_confidence = float(request.args.get('min_confidence', 0.6))
        
        # Get coordinator
        coordinator = get_coordinator()
        
        # Override confidence threshold if specified
        if min_confidence != coordinator.min_confidence:
            coordinator.set_confidence_threshold(min_confidence)
        
        # Make prediction
        result = coordinator.predict(symbol, validate=validate)
        
        # Return result
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logging.error(f"Prediction error for {symbol}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agentic_api.route('/feedback', methods=['POST'])
def feedback():
    """
    Provide feedback to the adaptive learning system.
    
    Expected JSON body:
    {
        "symbol": "AAPL",
        "predicted": 175.50,
        "actual": 177.25
    }
    
    Returns:
        JSON confirmation
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['symbol', 'predicted', 'actual']
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {missing_fields}'
            }), 400
        
        # Get coordinator
        coordinator = get_coordinator()
        
        # Update with actual
        coordinator.update_with_actual(
            symbol=data['symbol'],
            predicted=float(data['predicted']),
            actual=float(data['actual'])
        )
        
        return jsonify({
            'success': True,
            'message': 'Feedback received and processed'
        }), 200
        
    except Exception as e:
        logging.error(f"Feedback error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agentic_api.route('/performance', methods=['GET'])
def performance():
    """
    Get performance report for the agentic system.
    
    Returns:
        JSON with performance metrics
    """
    try:
        coordinator = get_coordinator()
        report = coordinator.get_performance_report()
        
        return jsonify({
            'success': True,
            'data': report
        }), 200
        
    except Exception as e:
        logging.error(f"Performance report error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agentic_api.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint.
    
    Returns:
        JSON with system health status
    """
    try:
        coordinator = get_coordinator()
        report = coordinator.get_performance_report()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'metrics': {
                'total_predictions': report['metrics']['total_predictions'],
                'average_confidence': report['metrics']['average_confidence'],
                'agents_initialized': True
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500


# Register blueprint helper
def register_agentic_api(app):
    """Register the agentic API blueprint with a Flask app"""
    app.register_blueprint(agentic_api)
    logging.info("Agentic API registered at /api/agentic")
