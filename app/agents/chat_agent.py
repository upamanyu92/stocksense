"""
Intelligent Chat Agent with self-awareness and learning capabilities
"""
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import random

from app.agents.base_agent import BaseAgent
from app.db.services.chat_service import ChatService
from app.db.services.stock_quote_service import StockQuoteService
from app.db.services.prediction_service import PredictionService
from app.db.services.watchlist_service import WatchlistDBService


logger = logging.getLogger(__name__)


class ChatAgent(BaseAgent):
    """
    Self-aware intelligent chat agent that learns from user interactions.
    
    Features:
    - Context-aware responses
    - Learns user preferences
    - Provides stock insights
    - Self-awareness about capabilities and limitations
    - Adaptive learning from feedback
    """
    
    def __init__(self):
        super().__init__(name="ChatAgent", confidence_threshold=0.7)
        
        # Self-awareness metadata
        self.capabilities = [
            "stock price queries",
            "prediction insights",
            "watchlist management",
            "market analysis",
            "learning from your preferences",
            "contextual conversations"
        ]
        
        self.limitations = [
            "I cannot make financial decisions for you",
            "I provide information, not financial advice",
            "My predictions are based on historical data and may not be accurate",
            "I'm constantly learning and may make mistakes"
        ]
        
        # Sentiment keywords
        self.positive_keywords = ['good', 'great', 'excellent', 'thanks', 'helpful', 'perfect', 'awesome']
        self.negative_keywords = ['bad', 'wrong', 'poor', 'unhelpful', 'incorrect', 'useless']
        
        # Intent patterns
        self.intent_patterns = {
            'greeting': [r'\b(hi|hello|hey|greetings)\b'],
            'goodbye': [r'\b(bye|goodbye|see you|farewell)\b'],
            'thanks': [r'\b(thank|thanks|appreciate)\b'],
            'stock_price': [r'\b(price|value|quote)\b.*\b(of|for)?\b.*\b([A-Z]{2,})\b', 
                           r'\b([A-Z]{2,})\b.*\b(price|value|quote)\b'],
            'prediction': [r'\b(predict|forecast|future)\b', r'\bwill\b.*\b(go|move|be)\b'],
            'watchlist': [r'\b(watchlist|watch|track|follow)\b'],
            'help': [r'\b(help|what can you|capabilities|can you)\b'],
            'about': [r'\b(who are you|what are you|about you)\b'],
            'learning': [r'\b(learn|remember|preference)\b']
        }
    
    def predict(self, symbol: str, data: Any) -> Dict[str, Any]:
        """Make prediction (for BaseAgent interface compatibility)"""
        return {'prediction': None, 'confidence': 0.0}
    
    def get_confidence(self, prediction: Any, data: Any) -> float:
        """Get confidence score"""
        return 0.8  # Default confidence for chat responses
    
    def chat(self, user_id: int, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process user message and generate intelligent response.
        
        Args:
            user_id: User ID
            message: User message
            context: Optional context (stock symbols, previous conversation, etc.)
            
        Returns:
            Response dictionary with message, context, and learning metadata
        """
        logger.info(f"Processing chat message from user {user_id}: {message}")
        
        # Get user preferences
        preferences = ChatService.get_user_preferences(user_id) or {}
        
        # Get conversation history for context
        history = ChatService.get_conversation_history(user_id, limit=5)
        
        # Detect intent
        intent = self._detect_intent(message)
        logger.info(f"Detected intent: {intent}")
        
        # Detect sentiment
        sentiment = self._detect_sentiment(message)
        
        # Generate response based on intent
        response_data = self._generate_response(
            user_id=user_id,
            message=message,
            intent=intent,
            sentiment=sentiment,
            preferences=preferences,
            history=history,
            context=context or {}
        )
        
        # Learn from this interaction
        self._learn_from_interaction(
            user_id=user_id,
            message=message,
            intent=intent,
            sentiment=sentiment,
            response=response_data['message']
        )
        
        # Save conversation
        ChatService.save_conversation(
            user_id=user_id,
            message=message,
            response=response_data['message'],
            context=response_data.get('context'),
            sentiment=sentiment
        )
        
        return response_data
    
    def _detect_intent(self, message: str) -> str:
        """Detect user intent from message"""
        message_lower = message.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    return intent
        
        return 'general'
    
    def _detect_sentiment(self, message: str) -> str:
        """Detect sentiment from message"""
        message_lower = message.lower()
        
        positive_count = sum(1 for word in self.positive_keywords if word in message_lower)
        negative_count = sum(1 for word in self.negative_keywords if word in message_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _generate_response(
        self,
        user_id: int,
        message: str,
        intent: str,
        sentiment: str,
        preferences: Dict,
        history: List[Dict],
        context: Dict
    ) -> Dict[str, Any]:
        """Generate intelligent response based on intent and context"""
        
        response_handlers = {
            'greeting': self._handle_greeting,
            'goodbye': self._handle_goodbye,
            'thanks': self._handle_thanks,
            'stock_price': self._handle_stock_price,
            'prediction': self._handle_prediction,
            'watchlist': self._handle_watchlist,
            'help': self._handle_help,
            'about': self._handle_about,
            'learning': self._handle_learning,
            'general': self._handle_general
        }
        
        handler = response_handlers.get(intent, self._handle_general)
        response = handler(user_id, message, preferences, history, context)
        
        # Add self-awareness elements
        if sentiment == 'negative':
            response['message'] += "\n\nI sense you might not be satisfied. I'm constantly learning to serve you better. Could you help me understand what you need?"
        
        return response
    
    def _handle_greeting(self, user_id: int, message: str, preferences: Dict, 
                        history: List, context: Dict) -> Dict[str, Any]:
        """Handle greeting messages"""
        greetings = [
            "Hello! I'm your StockSense AI assistant. I can help you with stock prices, predictions, and market insights. What would you like to know?",
            "Hi there! Ready to explore the market together? I can provide stock information, predictions, and learn your preferences. How can I assist you?",
            "Greetings! I'm here to help you make informed investment decisions. Ask me about stocks, predictions, or your watchlist!"
        ]
        
        response = random.choice(greetings)
        
        # Personalize based on history
        if len(history) > 0:
            response = f"Welcome back! {response}"
        
        # Mention preferred stocks if available
        if preferences.get('preferred_stocks'):
            stocks = ', '.join(preferences['preferred_stocks'][:3])
            response += f"\n\nI see you're interested in {stocks}. Would you like updates on these?"
        
        return {
            'message': response,
            'intent': 'greeting',
            'context': {'interaction_count': len(history)}
        }
    
    def _handle_goodbye(self, user_id: int, message: str, preferences: Dict,
                       history: List, context: Dict) -> Dict[str, Any]:
        """Handle goodbye messages"""
        farewells = [
            "Goodbye! I'll be here whenever you need market insights. Happy investing!",
            "See you later! I'm always learning to serve you better. Take care!",
            "Farewell! Remember, I'm here 24/7 to help with your stock queries. Until next time!"
        ]
        
        return {
            'message': random.choice(farewells),
            'intent': 'goodbye',
            'context': {}
        }
    
    def _handle_thanks(self, user_id: int, message: str, preferences: Dict,
                      history: List, context: Dict) -> Dict[str, Any]:
        """Handle thank you messages"""
        responses = [
            "You're welcome! I'm learning from our conversations to serve you better. Feel free to ask anything else!",
            "Happy to help! Each interaction helps me understand your preferences better. What else can I do for you?",
            "Glad I could assist! I'm constantly improving based on feedback like yours. Anything else you'd like to know?"
        ]
        
        # Mark this as positive feedback
        self.metadata['successful_predictions'] += 1
        
        return {
            'message': random.choice(responses),
            'intent': 'thanks',
            'context': {}
        }
    
    def _handle_stock_price(self, user_id: int, message: str, preferences: Dict,
                           history: List, context: Dict) -> Dict[str, Any]:
        """Handle stock price queries"""
        # Extract stock symbol from message
        symbols = re.findall(r'\b([A-Z]{2,})\b', message)
        
        if not symbols:
            return {
                'message': "I'd be happy to provide stock prices! Please specify a stock symbol (e.g., RELIANCE, TCS, INFY).",
                'intent': 'stock_price',
                'context': {}
            }
        
        symbol = symbols[0]
        
        try:
            # Get stock quote
            quote = StockQuoteService.get_stock_by_symbol(symbol)
            
            if quote:
                response = f"📊 **{quote.company_name}** ({symbol})\n\n"
                response += f"Current Price: ₹{quote.current_value:.2f}\n"
                response += f"Change: ₹{quote.change:.2f} ({quote.p_change:.2f}%)\n"
                response += f"Day High: ₹{quote.day_high:.2f} | Day Low: ₹{quote.day_low:.2f}\n"
                response += f"52-Week High: ₹{quote.week_52_high:.2f} | 52-Week Low: ₹{quote.week_52_low:.2f}\n"
                response += f"\nUpdated: {quote.updated_on}"
                
                # Add to user's preferred stocks for learning
                self._update_stock_preference(user_id, symbol)
                
                return {
                    'message': response,
                    'intent': 'stock_price',
                    'context': {'symbol': symbol, 'price': quote.current_value}
                }
            else:
                return {
                    'message': f"I couldn't find data for {symbol}. Please verify the symbol or try another stock.",
                    'intent': 'stock_price',
                    'context': {'symbol': symbol}
                }
        except Exception as e:
            logger.error(f"Error fetching stock price: {e}")
            return {
                'message': f"I encountered an issue while fetching {symbol} data. This helps me learn - I'll improve! Please try again.",
                'intent': 'stock_price',
                'context': {'symbol': symbol, 'error': str(e)}
            }
    
    def _handle_prediction(self, user_id: int, message: str, preferences: Dict,
                          history: List, context: Dict) -> Dict[str, Any]:
        """Handle prediction queries"""
        symbols = re.findall(r'\b([A-Z]{2,})\b', message)
        
        if not symbols:
            return {
                'message': "I can provide AI-powered predictions! Please specify a stock symbol (e.g., 'predict RELIANCE' or 'forecast for TCS').",
                'intent': 'prediction',
                'context': {}
            }
        
        symbol = symbols[0]
        
        try:
            # Get latest prediction
            predictions = PredictionService.get_predictions_by_symbol(symbol, limit=1)
            
            if predictions:
                pred = predictions[0]
                response = f"🔮 **AI Prediction for {symbol}**\n\n"
                response += f"Current Price: ₹{pred.current_price:.2f}\n"
                response += f"Predicted Price: ₹{pred.predicted_price:.2f}\n"
                
                change_pct = ((pred.predicted_price - pred.current_price) / pred.current_price) * 100
                direction = "↗️ increase" if change_pct > 0 else "↘️ decrease"
                response += f"Expected Change: {abs(change_pct):.2f}% {direction}\n"
                response += f"Prediction Date: {pred.prediction_date}\n\n"
                
                response += "⚠️ **Important**: This is an AI-generated prediction based on historical data. "
                response += "I'm learning to improve accuracy, but please don't rely solely on this for investment decisions. "
                response += "Always do your own research!"
                
                return {
                    'message': response,
                    'intent': 'prediction',
                    'context': {'symbol': symbol, 'predicted_price': pred.predicted_price}
                }
            else:
                return {
                    'message': f"I don't have predictions for {symbol} yet. Would you like me to generate one? I'm constantly learning to provide better forecasts!",
                    'intent': 'prediction',
                    'context': {'symbol': symbol}
                }
        except Exception as e:
            logger.error(f"Error fetching prediction: {e}")
            return {
                'message': f"I had trouble accessing prediction data for {symbol}. This helps me identify areas to improve. Please try again!",
                'intent': 'prediction',
                'context': {'symbol': symbol, 'error': str(e)}
            }
    
    def _handle_watchlist(self, user_id: int, message: str, preferences: Dict,
                         history: List, context: Dict) -> Dict[str, Any]:
        """Handle watchlist queries"""
        try:
            watchlist = WatchlistDBService.get_user_watchlist(user_id)
            
            if watchlist:
                response = f"📋 **Your Watchlist** ({len(watchlist)} stocks)\n\n"
                for item in watchlist[:5]:  # Show top 5
                    response += f"• {item.company_name} ({item.stock_symbol})\n"
                
                if len(watchlist) > 5:
                    response += f"\n... and {len(watchlist) - 5} more stocks"
                
                response += "\n\nI'm learning your preferences from your watchlist to provide better recommendations!"
            else:
                response = "Your watchlist is empty. Would you like me to suggest some stocks based on market trends? "
                response += "I learn from your choices to provide personalized recommendations!"
            
            return {
                'message': response,
                'intent': 'watchlist',
                'context': {'watchlist_count': len(watchlist) if watchlist else 0}
            }
        except Exception as e:
            logger.error(f"Error fetching watchlist: {e}")
            return {
                'message': "I had trouble accessing your watchlist. I'm learning from these issues to improve reliability!",
                'intent': 'watchlist',
                'context': {'error': str(e)}
            }
    
    def _handle_help(self, user_id: int, message: str, preferences: Dict,
                    history: List, context: Dict) -> Dict[str, Any]:
        """Handle help requests"""
        response = "🤖 **I'm your AI-powered StockSense Assistant!**\n\n"
        response += "**What I can do:**\n"
        for cap in self.capabilities:
            response += f"• {cap}\n"
        
        response += "\n**My limitations:**\n"
        for lim in self.limitations:
            response += f"• {lim}\n"
        
        response += "\n**Examples:**\n"
        response += "• 'What's the price of RELIANCE?'\n"
        response += "• 'Predict TCS stock'\n"
        response += "• 'Show my watchlist'\n"
        response += "• 'Tell me about yourself'\n"
        
        response += "\n💡 I learn from every interaction to serve you better!"
        
        return {
            'message': response,
            'intent': 'help',
            'context': {'capabilities_shown': True}
        }
    
    def _handle_about(self, user_id: int, message: str, preferences: Dict,
                     history: List, context: Dict) -> Dict[str, Any]:
        """Handle questions about the agent itself"""
        response = "🧠 **About Me**\n\n"
        response += "I'm an AI chat agent built specifically for StockSense. Here's what makes me unique:\n\n"
        response += "**Self-Aware**: I understand my capabilities AND limitations\n"
        response += "**Always Learning**: I learn from every conversation to improve my responses\n"
        response += "**Context-Aware**: I remember our conversations and your preferences\n"
        response += "**Honest**: I tell you when I'm uncertain or when I make mistakes\n"
        response += "**Helpful**: My goal is to help you make informed decisions\n\n"
        
        response += f"**My Stats:**\n"
        response += f"• Conversations with you: {len(history)}\n"
        response += f"• Total predictions made: {self.metadata['predictions_made']}\n"
        response += f"• Success rate: {self.get_accuracy():.1%}\n\n"
        
        response += "I'm constantly evolving. Your feedback helps me improve! 🚀"
        
        return {
            'message': response,
            'intent': 'about',
            'context': {'self_awareness': True}
        }
    
    def _handle_learning(self, user_id: int, message: str, preferences: Dict,
                        history: List, context: Dict) -> Dict[str, Any]:
        """Handle questions about learning"""
        response = "📚 **How I Learn**\n\n"
        response += "I improve through multiple mechanisms:\n\n"
        response += "1. **Conversation Patterns**: I analyze successful interactions\n"
        response += "2. **User Preferences**: I track stocks you're interested in\n"
        response += "3. **Feedback**: Positive/negative sentiment helps me adjust\n"
        response += "4. **Context Memory**: I remember our conversation history\n"
        response += "5. **Performance Tracking**: I monitor my accuracy and improve\n\n"
        
        if preferences.get('preferred_stocks'):
            response += f"For example, I've learned you're interested in: {', '.join(preferences['preferred_stocks'][:3])}\n\n"
        
        response += "Every interaction makes me smarter! Keep chatting with me to help me serve you better. 🎓"
        
        return {
            'message': response,
            'intent': 'learning',
            'context': {'learning_explained': True}
        }
    
    def _handle_general(self, user_id: int, message: str, preferences: Dict,
                       history: List, context: Dict) -> Dict[str, Any]:
        """Handle general queries"""
        responses = [
            "I'm here to help with stock market insights! Try asking me about stock prices, predictions, or your watchlist. "
            "I'm learning to understand more types of questions, so feel free to experiment!",
            
            "I can provide information on stocks, predictions, and market data. What specific information are you looking for? "
            "The more we chat, the better I understand your needs!",
            
            "I'm your AI assistant for stock market analysis. While I'm still learning to handle all types of questions, "
            "I'm great at providing stock prices, predictions, and watchlist information. What can I help you with?"
        ]
        
        response = random.choice(responses)
        
        # Suggest based on preferences
        if preferences.get('preferred_stocks'):
            stock = random.choice(preferences['preferred_stocks'])
            response += f"\n\nBy the way, would you like an update on {stock}? I remember you're interested in it!"
        
        return {
            'message': response,
            'intent': 'general',
            'context': {}
        }
    
    def _learn_from_interaction(
        self,
        user_id: int,
        message: str,
        intent: str,
        sentiment: str,
        response: str
    ):
        """Learn from the interaction"""
        # Update metadata
        self.metadata['predictions_made'] += 1
        
        # Track sentiment as success metric
        if sentiment == 'positive':
            self.metadata['successful_predictions'] += 1
        
        # Update interaction style preference
        message_length = len(message.split())
        if message_length < 5:
            interaction_style = 'concise'
        elif message_length < 15:
            interaction_style = 'moderate'
        else:
            interaction_style = 'detailed'
        
        # Update user preferences
        current_prefs = ChatService.get_user_preferences(user_id) or {}
        topics = current_prefs.get('topics_of_interest', [])
        
        # Add intent to topics of interest
        if intent not in topics and intent != 'general':
            topics.append(intent)
            topics = topics[-10:]  # Keep last 10 topics
        
        ChatService.update_user_preferences(
            user_id=user_id,
            interaction_style=interaction_style,
            topics_of_interest=topics
        )
        
        logger.info(f"Learned from interaction - Intent: {intent}, Sentiment: {sentiment}")
    
    def _update_stock_preference(self, user_id: int, symbol: str):
        """Update user's preferred stocks"""
        prefs = ChatService.get_user_preferences(user_id) or {}
        preferred = prefs.get('preferred_stocks', [])
        
        if symbol not in preferred:
            preferred.append(symbol)
            preferred = preferred[-20:]  # Keep last 20 stocks
            
            ChatService.update_user_preferences(
                user_id=user_id,
                preferred_stocks=preferred
            )
