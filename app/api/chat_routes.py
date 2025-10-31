"""
Chat API routes for intelligent agent interactions
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
import logging

from app.agents.chat_agent import ChatAgent
from app.db.services.chat_service import ChatService

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

# Initialize chat agent
chat_agent = ChatAgent()


@chat_bp.route('/message', methods=['POST'])
@login_required
def send_message():
    """
    Send a message to the chat agent and get response.
    
    Request JSON:
        {
            "message": "User message",
            "context": {...}  // Optional context
        }
    
    Response:
        {
            "response": "Agent response",
            "intent": "detected_intent",
            "sentiment": "detected_sentiment",
            "context": {...}
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        message = data['message'].strip()
        context = data.get('context', {})
        
        if not message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Process message through chat agent
        response_data = chat_agent.chat(
            user_id=current_user.id,
            message=message,
            context=context
        )
        
        return jsonify({
            'success': True,
            'response': response_data['message'],
            'intent': response_data.get('intent'),
            'context': response_data.get('context', {})
        })
    
    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to process message',
            'message': 'I apologize, but I encountered an error. I\'m learning from this to prevent future issues!'
        }), 500


@chat_bp.route('/history', methods=['GET'])
@login_required
def get_history():
    """
    Get conversation history for current user.
    
    Query params:
        limit: Number of messages to retrieve (default: 10, max: 50)
    
    Response:
        {
            "history": [
                {
                    "id": 1,
                    "message": "user message",
                    "response": "agent response",
                    "sentiment": "positive",
                    "created_at": "timestamp"
                },
                ...
            ]
        }
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        limit = min(limit, 50)  # Cap at 50
        
        history = ChatService.get_conversation_history(
            user_id=current_user.id,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'history': history
        })
    
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch chat history'}), 500


@chat_bp.route('/preferences', methods=['GET'])
@login_required
def get_preferences():
    """
    Get learned user preferences.
    
    Response:
        {
            "preferred_stocks": ["RELIANCE", "TCS", ...],
            "interaction_style": "concise|moderate|detailed",
            "topics_of_interest": ["stock_price", "prediction", ...],
            "learning_data": {...}
        }
    """
    try:
        preferences = ChatService.get_user_preferences(current_user.id)
        
        if not preferences:
            return jsonify({
                'success': True,
                'preferences': {
                    'preferred_stocks': [],
                    'interaction_style': 'moderate',
                    'topics_of_interest': [],
                    'learning_data': {}
                }
            })
        
        return jsonify({
            'success': True,
            'preferences': preferences
        })
    
    except Exception as e:
        logger.error(f"Error fetching preferences: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch preferences'}), 500


@chat_bp.route('/preferences', methods=['PUT'])
@login_required
def update_preferences():
    """
    Update user preferences manually.
    
    Request JSON:
        {
            "preferred_stocks": ["RELIANCE", "TCS"],
            "interaction_style": "concise"
        }
    """
    try:
        data = request.get_json()
        
        ChatService.update_user_preferences(
            user_id=current_user.id,
            preferred_stocks=data.get('preferred_stocks'),
            interaction_style=data.get('interaction_style'),
            topics_of_interest=data.get('topics_of_interest')
        )
        
        return jsonify({
            'success': True,
            'message': 'Preferences updated successfully'
        })
    
    except Exception as e:
        logger.error(f"Error updating preferences: {e}", exc_info=True)
        return jsonify({'error': 'Failed to update preferences'}), 500


@chat_bp.route('/stats', methods=['GET'])
@login_required
def get_agent_stats():
    """
    Get chat agent statistics and performance metrics.
    
    Response:
        {
            "total_conversations": 100,
            "success_rate": 0.85,
            "capabilities": [...],
            "limitations": [...]
        }
    """
    try:
        history = ChatService.get_conversation_history(current_user.id, limit=100)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_conversations': len(history),
                'success_rate': chat_agent.get_accuracy(),
                'capabilities': chat_agent.capabilities,
                'limitations': chat_agent.limitations,
                'agent_metadata': chat_agent.metadata
            }
        })
    
    except Exception as e:
        logger.error(f"Error fetching agent stats: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch agent stats'}), 500


@chat_bp.route('/clear-history', methods=['DELETE'])
@login_required
def clear_history():
    """
    Clear conversation history for current user.
    WARNING: This cannot be undone.
    """
    try:
        # This would require implementing a delete method in ChatService
        # For now, return not implemented
        return jsonify({
            'success': False,
            'message': 'Clear history feature coming soon'
        }), 501
    
    except Exception as e:
        logger.error(f"Error clearing history: {e}", exc_info=True)
        return jsonify({'error': 'Failed to clear history'}), 500


# Initialize chat tables on blueprint registration
try:
    ChatService.create_tables()
    logger.info("Chat tables initialized successfully")
except Exception as e:
    logger.error(f"Error initializing chat tables: {e}", exc_info=True)
