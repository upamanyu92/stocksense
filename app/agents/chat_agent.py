"""
Intelligent Chat Agent with Ollama LLM integration for natural language understanding
"""
import re
import logging
from typing import Dict, List, Optional, Any
import random

from app.agents.base_agent import BaseAgent
from app.db.services.chat_service import ChatService
from app.db.services.prediction_service import PredictionService
from app.db.services.watchlist_service import WatchlistDBService
from app.services.ollama_chat_service import OllamaChatService
from app.services.nse_securities_service import NSESecuritiesService
from app.db.session_manager import get_session_manager


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
        
        # Initialize Ollama chat service
        self.ollama_service = OllamaChatService()
        self.nse_service = NSESecuritiesService()

        # Self-awareness metadata
        self.capabilities = [
            "stock price queries",
            "prediction insights",
            "watchlist management",
            "market analysis",
            "NSE securities search and management",
            "contextual conversations",
            "intelligent understanding via Ollama LLM"
        ]
        
        self.limitations = [
            "I cannot make financial decisions for you",
            "I provide information, not financial advice",
            "My predictions are based on historical data and may not be accurate",
            "I'm constantly learning and may make mistakes"
        ]

    def predict(self, symbol: str, data: Any) -> Dict[str, Any]:
        """Make prediction (for BaseAgent interface compatibility)"""
        return {'prediction': None, 'confidence': 0.0}
    
    def get_confidence(self, prediction: Any, data: Any) -> float:
        """Get confidence score"""
        return 0.8  # Default confidence for chat responses
    
    def chat(self, user_id: int, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process user message using Ollama LLM and generate intelligent response.

        Args:
            user_id: User ID
            message: User message
            context: Optional context (stock symbols, previous conversation, etc.)
            
        Returns:
            Response dictionary with message, intent, action, and entities
        """
        logger.info(f"Processing chat message from user {user_id}: {message}")
        
        try:
            # Get user preferences
            preferences = ChatService.get_user_preferences(user_id) or {}

            # Get conversation history for context
            history = ChatService.get_conversation_history(user_id, limit=5)

            # Build context for Ollama
            ollama_context = self._build_ollama_context(user_id, preferences, context)

            # Process through Ollama LLM
            ollama_response = self.ollama_service.process_user_message(
                message,
                context=ollama_context,
                conversation_history=history
            )

            if not ollama_response.get('success'):
                return {
                    'message': ollama_response.get('response', 'I apologize, but I encountered an error.'),
                    'intent': 'error',
                    'context': {}
                }

            # Extract intent and action from Ollama response
            intent = ollama_response.get('intent', 'general')
            action = ollama_response.get('action')
            entities = ollama_response.get('entities', {})

            # Generate contextual response based on action
            final_response = self._handle_action(
                user_id=user_id,
                action=action,
                entities=entities,
                intent=intent,
                llm_response=ollama_response.get('response'),
                preferences=preferences,
                context=context or {}
            )

            # Learn from this interaction
            self._learn_from_interaction(
                user_id=user_id,
                message=message,
                intent=intent,
                response=final_response['message'],
                action=action,
                entities=entities
            )

            # Save conversation
            ChatService.save_conversation(
                user_id=user_id,
                message=message,
                response=final_response['message'],
                context={'intent': intent, 'action': action, 'entities': entities},
                sentiment='neutral'
            )

            return final_response

        except Exception as e:
            logger.error(f"Error in chat: {e}", exc_info=True)
            return {
                'message': 'I apologize, but I encountered an error. Please try again.',
                'intent': 'error',
                'context': {}
            }

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
            # Get stock data directly from database
            db = get_session_manager()
            row = db.fetch_one('''
                SELECT security_id, company_name, current_value, change, p_change, 
                       day_high, day_low, high_52week, low_52week, updated_on
                FROM stock_quotes 
                WHERE UPPER(security_id) = UPPER(?) OR UPPER(company_name) LIKE UPPER(?)
                LIMIT 1
            ''', (symbol, f'%{symbol}%'))
            
            if row:
                # Explicit field mapping for safety
                quote_data = {
                    'security_id': row['security_id'],
                    'company_name': row['company_name'],
                    'current_value': row['current_value'],
                    'change': row['change'],
                    'p_change': row['p_change'],
                    'day_high': row['day_high'],
                    'day_low': row['day_low'],
                    'high_52week': row['high_52week'],
                    'low_52week': row['low_52week'],
                    'updated_on': row['updated_on']
                }
                response = f"📊 **{quote_data['company_name']}** ({quote_data['security_id']})\n\n"
                response += f"Current Price: ₹{quote_data['current_value']:.2f}\n"
                response += f"Change: ₹{quote_data['change']:.2f} ({quote_data['p_change']:.2f}%)\n"
                response += f"Day High: ₹{quote_data['day_high']:.2f} | Day Low: ₹{quote_data['day_low']:.2f}\n"
                response += f"52-Week High: ₹{quote_data['high_52week']:.2f} | 52-Week Low: ₹{quote_data['low_52week']:.2f}\n"
                response += f"\nUpdated: {quote_data['updated_on']}"
                
                # Add to user's preferred stocks for learning
                self._update_stock_preference(user_id, quote_data['security_id'])
                
                return {
                    'message': response,
                    'intent': 'stock_price',
                    'context': {'symbol': quote_data['security_id'], 'price': quote_data['current_value']}
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
            # Get all predictions and filter by symbol (security_id)
            all_predictions = PredictionService.get_all(limit=100)
            predictions = [p for p in all_predictions if p.stock_symbol and p.stock_symbol.upper() == symbol.upper()]
            
            # If no exact match, try by security_id in the database
            if not predictions:
                predictions = [p for p in all_predictions if symbol.upper() in (p.company_name or '').upper()]
            
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
            watchlist = WatchlistDBService.get_by_user(user_id)
            
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
        response: str,
        action: Optional[str] = None,
        entities: Optional[Dict] = None
    ):
        """Learn from the interaction"""
        # Update metadata
        self.metadata['predictions_made'] += 1
        
        # Track action usage
        if action:
            actions_used = self.metadata.get('actions_used', {})
            actions_used[action] = actions_used.get(action, 0) + 1
            self.metadata['actions_used'] = actions_used

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
        
        # Track symbols if mentioned
        symbols_tracked = current_prefs.get('symbols_tracked', [])
        if entities and entities.get('symbols'):
            for sym in entities['symbols']:
                if sym not in symbols_tracked:
                    symbols_tracked.append(sym)
            symbols_tracked = symbols_tracked[-20:]

        ChatService.update_user_preferences(
            user_id=user_id,
            interaction_style=interaction_style,
            topics_of_interest=topics,
            preferred_stocks=entities.get('symbols', []) if entities else []
        )
        
        logger.info(f"Learned from interaction - Intent: {intent}, Action: {action}")

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

    def _build_ollama_context(self, user_id: int, preferences: Dict, context: Optional[Dict]) -> Dict[str, Any]:
        """Build context information for Ollama LLM"""
        try:
            db = get_session_manager()

            # Get user's watchlist
            watchlist = WatchlistDBService.get_by_user(user_id)
            watchlist_symbols = [w.stock_symbol for w in watchlist] if watchlist else []

            # Get available NSE stocks count using a pooled connection
            conn = db.get_connection()
            try:
                stocks_count = self.nse_service.get_security_count(conn)
            finally:
                db.release_connection(conn)

            return {
                'watchlist': watchlist_symbols,
                'current_stocks': context.get('symbols', []) if context else [],
                'stocks_available': stocks_count,
                'user_preferences': preferences
            }
        except Exception as e:
            logger.error(f"Error building Ollama context: {e}")
            return {}

    def _handle_action(self, user_id: int, action: Optional[str], entities: Dict,
                      intent: str, llm_response: str, preferences: Dict, context: Dict) -> Dict[str, Any]:
        """Handle action detected by Ollama LLM"""

        handlers = {
            'get_stock_price': lambda: self._handle_get_price(user_id, entities, llm_response),
            'run_prediction': lambda: self._handle_run_prediction(user_id, entities, llm_response),
            'add_watchlist': lambda: self._handle_add_watchlist(user_id, entities, llm_response),
            'remove_watchlist': lambda: self._handle_remove_watchlist(user_id, entities, llm_response),
            'view_watchlist': lambda: self._handle_view_watchlist(user_id, llm_response),
            'display_stock_values': lambda: self._handle_display_values(user_id, entities, llm_response),
            'list_available_stocks': lambda: self._handle_list_stocks(user_id, entities, llm_response),
        }

        handler = handlers.get(action)
        if handler:
            try:
                return handler()
            except Exception as e:
                logger.error(f"Error handling action {action}: {e}")
                return {
                    'message': f"I encountered an error handling your request: {str(e)}",
                    'intent': intent,
                    'context': {}
                }

        # No specific action, return LLM response
        return {
            'message': llm_response,
            'intent': intent,
            'context': entities
        }

    def _handle_get_price(self, user_id: int, entities: Dict, llm_response: str) -> Dict[str, Any]:
        """Handle getting stock price"""
        symbols = entities.get('symbols', [])

        if not symbols:
            return {
                'message': llm_response + '\n\nPlease specify which stock symbol you\'d like to check.',
                'intent': 'check_price',
                'context': {}
            }

        db = get_session_manager()
        prices_info = []

        for symbol in symbols[:3]:  # Limit to 3 symbols
            try:
                row = db.fetch_one('''
                    SELECT company_name, current_value, change, p_change, day_high, day_low
                    FROM stock_quotes 
                    WHERE UPPER(security_id) = UPPER(?) OR UPPER(company_name) LIKE UPPER(?)
                    LIMIT 1
                ''', (symbol, f'%{symbol}%'))

                if row:
                    prices_info.append({
                        'symbol': symbol,
                        'company': row['company_name'],
                        'price': row['current_value'],
                        'change': row['change'],
                        'pchange': row['p_change'],
                        'high': row['day_high'],
                        'low': row['day_low']
                    })
            except Exception as e:
                logger.error(f"Error getting price for {symbol}: {e}")

        if not prices_info:
            return {
                'message': f"I couldn't find price information for {', '.join(symbols)}. Would you like me to search for available stocks?",
                'intent': 'check_price',
                'context': {}
            }

        price_text = llm_response + "\n\n**Stock Prices:**\n"
        for info in prices_info:
            price_text += f"\n{info['symbol']} ({info['company']}): ₹{info['price']}\n"
            price_text += f"  Change: {info['change']} ({info['pchange']}%)\n"
            price_text += f"  Range: ₹{info['low']} - ₹{info['high']}"

        return {
            'message': price_text,
            'intent': 'check_price',
            'context': {'symbols': symbols, 'prices': prices_info}
        }

    def _handle_run_prediction(self, user_id: int, entities: Dict, llm_response: str) -> Dict[str, Any]:
        """Handle running predictions"""
        scope = entities.get('prediction_scope', 'single')
        symbols = entities.get('symbols', [])

        return {
            'message': llm_response + f"\n\nTo run predictions on {scope} stocks" +
                      (f" ({', '.join(symbols)})" if symbols else "(your watchlist)") +
                      ", use the prediction endpoint or click 'Run Predictions' in the UI.",
            'intent': 'predict',
            'context': {'scope': scope, 'symbols': symbols}
        }

    def _handle_add_watchlist(self, user_id: int, entities: Dict, llm_response: str) -> Dict[str, Any]:
        """Handle adding to watchlist"""
        symbols = entities.get('symbols', [])

        if not symbols:
            return {
                'message': llm_response + '\n\nPlease specify which stocks to add to your watchlist.',
                'intent': 'watchlist',
                'context': {}
            }

        try:
            added = []

            for symbol in symbols:
                # Get stock info from database
                db = get_session_manager()
                row = db.fetch_one('''
                    SELECT id, company_name FROM stock_quotes 
                    WHERE UPPER(security_id) = UPPER(?)
                    LIMIT 1
                ''', (symbol,))

                if row:
                    stock_id = row['id']
                    company_name = row['company_name']
                    # Add to watchlist using the correct method
                    success = WatchlistDBService.add(user_id, symbol, company_name)
                    if success:
                        added.append(symbol)


            if added:
                return {
                    'message': f"✅ Added {', '.join(added)} to your watchlist!",
                    'intent': 'watchlist',
                    'context': {'action': 'add', 'symbols': added}
                }
            else:
                return {
                    'message': f"Couldn't find {', '.join(symbols)} in available stocks.",
                    'intent': 'watchlist',
                    'context': {}
                }
        except Exception as e:
            logger.error(f"Error adding to watchlist: {e}")
            return {
                'message': f"Error adding to watchlist: {str(e)}",
                'intent': 'watchlist',
                'context': {}
            }

    def _handle_remove_watchlist(self, user_id: int, entities: Dict, llm_response: str) -> Dict[str, Any]:
        """Handle removing from watchlist"""
        symbols = entities.get('symbols', [])

        return {
            'message': llm_response + (f"\n\nTo remove {', '.join(symbols)} from your watchlist, use the UI or call the remove endpoint." if symbols else ""),
            'intent': 'watchlist',
            'context': {'action': 'remove', 'symbols': symbols}
        }

    def _handle_view_watchlist(self, user_id: int, llm_response: str) -> Dict[str, Any]:
        """Handle viewing watchlist"""
        try:
            watchlist = WatchlistDBService.get_by_user(user_id)

            if watchlist:
                watchlist_text = llm_response + "\n\n**Your Watchlist:**\n"
                for item in watchlist:
                    watchlist_text += f"- {item.stock_symbol}: {item.company_name}\n"

                return {
                    'message': watchlist_text,
                    'intent': 'watchlist',
                    'context': {'action': 'view', 'count': len(watchlist)}
                }
            else:
                return {
                    'message': "Your watchlist is empty. Would you like to add some stocks?",
                    'intent': 'watchlist',
                    'context': {'count': 0}
                }
        except Exception as e:
            logger.error(f"Error viewing watchlist: {e}")
            return {
                'message': f"Error viewing watchlist: {str(e)}",
                'intent': 'watchlist',
                'context': {}
            }

    def _handle_display_values(self, user_id: int, entities: Dict, llm_response: str) -> Dict[str, Any]:
        """Handle displaying current and predicted values"""
        symbols = entities.get('symbols', [])

        return {
            'message': llm_response + (f"\n\nDisplaying current and predicted values for: {', '.join(symbols)}" if symbols else ""),
            'intent': 'show_values',
            'context': {'symbols': symbols}
        }

    def _handle_list_stocks(self, user_id: int, entities: Dict, llm_response: str) -> Dict[str, Any]:
        """Handle listing available NSE stocks"""
        try:
            db = get_session_manager()
            conn = db.get_connection()
            try:
                search_query = entities.get('search_query')
                if search_query:
                    stocks = self.nse_service.search_securities(conn, search_query)
                    title = f"Found {len(stocks)} matching stocks:"
                else:
                    stocks = self.nse_service.get_available_securities(conn, limit=20)
                    title = f"Top 20 available NSE stocks (total: {self.nse_service.get_security_count(conn)}):"
            finally:
                db.release_connection(conn)

            if stocks:
                stocks_text = llm_response + f"\n\n**{title}**\n"
                for stock in stocks:
                    stocks_text += f"- {stock['scrip_code']}: {stock['company_name']}\n"

                return {
                    'message': stocks_text,
                    'intent': 'list_stocks',
                    'context': {'count': len(stocks), 'stocks': stocks}
                }
            else:
                return {
                    'message': "No stocks found matching your query.",
                    'intent': 'list_stocks',
                    'context': {}
                }
        except Exception as e:
            logger.error(f"Error listing stocks: {e}")
            return {
                'message': f"Error listing stocks: {str(e)}",
                'intent': 'list_stocks',
                'context': {}
            }
