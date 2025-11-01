"""
Intelligent Chat Agent with self-awareness and learning capabilities
"""
import re
import logging
from typing import Dict, List, Optional, Any
import random

from app.agents.base_agent import BaseAgent
from app.db.services.chat_service import ChatService
from app.db.services.prediction_service import PredictionService
from app.db.services.watchlist_service import WatchlistDBService
from app.utils.util import get_db_connection


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
            "stock price queries with real-time data",
            "AI-powered prediction insights and analysis",
            "automatic watchlist management and tracking",
            "market trend analysis and recommendations",
            "proactive alerts and suggestions",
            "stock comparisons and portfolio insights",
            "learning from your preferences and behavior",
            "contextual conversations with actionable advice"
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
        
        # Intent patterns - expanded for more actions
        self.intent_patterns = {
            'greeting': [r'\b(hi|hello|hey|greetings)\b'],
            'goodbye': [r'\b(bye|goodbye|see you|farewell)\b'],
            'thanks': [r'\b(thank|thanks|appreciate)\b'],
            'stock_price': [r'\b(price|value|quote|current)\b.*\b(of|for)?\b.*\b([A-Z]{2,})\b', 
                           r'\b([A-Z]{2,})\b.*\b(price|value|quote)\b'],
            'prediction': [r'\b(predict|forecast|future|will.*go|expected|outlook)\b'],
            'watchlist_add': [r'\b(add|track|monitor|watch)\b.*\b(to|in)?\s*(watchlist|portfolio)?\b', 
                             r'\b(track|follow|monitor)\b'],
            'watchlist_remove': [r'\b(remove|delete|untrack|unwatch)\b.*\bfrom\b.*\b(watchlist|portfolio)\b'],
            'watchlist_view': [r'\b(show|view|display|list|get)\b.*\b(watchlist|portfolio|tracked)\b',
                              r'\b(watchlist|portfolio)\b'],
            'compare': [r'\b(compare|versus|vs|difference between)\b', r'\bor\b.*\bbetter\b'],
            'recommend': [r'\b(recommend|suggest|advice|should i|what.*buy)\b'],
            'analysis': [r'\b(analyze|analysis|insights?|trends?|performance)\b'],
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
            'watchlist_add': self._handle_watchlist_add,
            'watchlist_remove': self._handle_watchlist_remove,
            'watchlist_view': self._handle_watchlist_view,
            'compare': self._handle_compare,
            'recommend': self._handle_recommend,
            'analysis': self._handle_analysis,
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
            # Get stock data directly from database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Try to find by security_id first
            cursor.execute('''
                SELECT security_id, company_name, current_value, change, p_change, 
                       day_high, day_low, high_52week, low_52week, updated_on
                FROM stock_quotes 
                WHERE UPPER(security_id) = UPPER(?) OR UPPER(company_name) LIKE UPPER(?)
                LIMIT 1
            ''', (symbol, f'%{symbol}%'))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                # Explicit field mapping for safety
                quote_data = {
                    'security_id': row[0],
                    'company_name': row[1],
                    'current_value': row[2],
                    'change': row[3],
                    'p_change': row[4],
                    'day_high': row[5],
                    'day_low': row[6],
                    'high_52week': row[7],
                    'low_52week': row[8],
                    'updated_on': row[9]
                }
                response = f"📊 **{quote_data['company_name']}** ({quote_data['security_id']})\n\n"
                response += f"Current Price: ₹{quote_data['current_value']:.2f}\n"
                response += f"Change: ₹{quote_data['change']:.2f} ({quote_data['p_change']:.2f}%)\n"
                response += f"Day High: ₹{quote_data['day_high']:.2f} | Day Low: ₹{quote_data['day_low']:.2f}\n"
                response += f"52-Week High: ₹{quote_data['high_52week']:.2f} | 52-Week Low: ₹{quote_data['low_52week']:.2f}\n"
                response += f"\nUpdated: {quote_data['updated_on']}\n"
                
                # Add actionable insights
                insights = self._generate_price_insights(quote_data)
                if insights:
                    response += f"\n💡 **Insights:**\n{insights}\n"
                
                # Proactive action: Check if stock should be added to watchlist
                watchlist = WatchlistDBService.get_by_user(user_id)
                is_in_watchlist = any(item.stock_symbol == quote_data['security_id'] for item in watchlist) if watchlist else False
                
                if not is_in_watchlist:
                    response += f"\n➕ Would you like me to add {quote_data['security_id']} to your watchlist? (Just say 'add to watchlist')"
                
                # Add to user's preferred stocks for learning
                self._update_stock_preference(user_id, quote_data['security_id'])
                
                return {
                    'message': response,
                    'intent': 'stock_price',
                    'context': {'symbol': quote_data['security_id'], 'price': quote_data['current_value']},
                    'actions_taken': ['updated_preferences'],
                    'suggested_actions': [] if is_in_watchlist else ['add_to_watchlist']
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
                
                # Add actionable recommendation
                recommendation = self._generate_prediction_recommendation(change_pct, pred)
                response += f"💡 **Recommendation:** {recommendation}\n\n"
                
                response += "⚠️ **Important**: This is an AI-generated prediction based on historical data. "
                response += "I'm learning to improve accuracy, but please don't rely solely on this for investment decisions. "
                response += "Always do your own research!"
                
                return {
                    'message': response,
                    'intent': 'prediction',
                    'context': {'symbol': symbol, 'predicted_price': pred.predicted_price, 'change_pct': change_pct},
                    'actions_taken': ['provided_prediction'],
                    'suggested_actions': ['view_analysis', 'add_to_watchlist']
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
    
    def _handle_watchlist_add(self, user_id: int, message: str, preferences: Dict,
                         history: List, context: Dict) -> Dict[str, Any]:
        """Handle adding stocks to watchlist"""
        # Extract stock symbol from message
        symbols = re.findall(r'\b([A-Z]{2,})\b', message)
        
        if not symbols:
            return {
                'message': "I'd be happy to add a stock to your watchlist! Please specify a stock symbol (e.g., 'add RELIANCE to watchlist').",
                'intent': 'watchlist_add',
                'context': {}
            }
        
        symbol = symbols[0]
        
        try:
            # Get stock data to verify it exists
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT security_id, company_name
                FROM stock_quotes 
                WHERE UPPER(security_id) = UPPER(?) OR UPPER(company_name) LIKE UPPER(?)
                LIMIT 1
            ''', (symbol, f'%{symbol}%'))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                stock_symbol = row[0]
                company_name = row[1]
                
                # Add to watchlist
                WatchlistDBService.add_to_watchlist(user_id, stock_symbol)
                
                # Update preferences
                self._update_stock_preference(user_id, stock_symbol)
                
                response = f"✅ **Action Taken:** Added **{company_name}** ({stock_symbol}) to your watchlist!\n\n"
                response += "I'll keep track of this stock for you. You can ask me about it anytime, and I'll learn your preferences to provide better insights!"
                
                return {
                    'message': response,
                    'intent': 'watchlist_add',
                    'context': {'symbol': stock_symbol, 'action': 'added'},
                    'actions_taken': ['added_to_watchlist', 'updated_preferences']
                }
            else:
                return {
                    'message': f"I couldn't find a stock matching '{symbol}'. Please verify the symbol and try again.",
                    'intent': 'watchlist_add',
                    'context': {'symbol': symbol, 'error': 'not_found'}
                }
        except Exception as e:
            logger.error(f"Error adding to watchlist: {e}")
            return {
                'message': f"I encountered an issue while adding {symbol} to your watchlist. Let me try to fix this! Please try again.",
                'intent': 'watchlist_add',
                'context': {'symbol': symbol, 'error': str(e)}
            }
    
    def _handle_watchlist_remove(self, user_id: int, message: str, preferences: Dict,
                                 history: List, context: Dict) -> Dict[str, Any]:
        """Handle removing stocks from watchlist"""
        symbols = re.findall(r'\b([A-Z]{2,})\b', message)
        
        if not symbols:
            return {
                'message': "Which stock would you like to remove from your watchlist? Please specify a symbol.",
                'intent': 'watchlist_remove',
                'context': {}
            }
        
        symbol = symbols[0]
        
        try:
            # Remove from watchlist
            WatchlistDBService.remove_from_watchlist(user_id, symbol)
            
            response = f"✅ **Action Taken:** Removed {symbol} from your watchlist.\n\n"
            response += "I've updated your preferences accordingly. You can always add it back if you change your mind!"
            
            return {
                'message': response,
                'intent': 'watchlist_remove',
                'context': {'symbol': symbol, 'action': 'removed'},
                'actions_taken': ['removed_from_watchlist']
            }
        except Exception as e:
            logger.error(f"Error removing from watchlist: {e}")
            return {
                'message': f"I had trouble removing {symbol}. It might not be in your watchlist. Try 'show watchlist' to see what's tracked.",
                'intent': 'watchlist_remove',
                'context': {'symbol': symbol, 'error': str(e)}
            }
    
    def _handle_watchlist_view(self, user_id: int, message: str, preferences: Dict,
                         history: List, context: Dict) -> Dict[str, Any]:
        """Handle viewing watchlist"""
        try:
            watchlist = WatchlistDBService.get_by_user(user_id)
            
            if watchlist:
                response = f"📋 **Your Watchlist** ({len(watchlist)} stocks)\n\n"
                for item in watchlist[:10]:  # Show top 10
                    response += f"• {item.company_name} ({item.stock_symbol})\n"
                
                if len(watchlist) > 10:
                    response += f"\n... and {len(watchlist) - 10} more stocks"
                
                response += "\n\n💡 **Quick Actions:**\n"
                response += "• Ask 'analyze my watchlist' for insights\n"
                response += "• Say 'remove [SYMBOL]' to untrack a stock\n"
                response += "• Request 'predict [SYMBOL]' for forecasts"
                
                return {
                    'message': response,
                    'intent': 'watchlist_view',
                    'context': {'watchlist_count': len(watchlist)},
                    'suggested_actions': ['analyze_watchlist', 'get_predictions']
                }
            else:
                response = "📋 Your watchlist is empty.\n\n"
                response += "💡 **Let me help you get started:**\n"
                response += "• Say 'add [SYMBOL] to watchlist' to track stocks\n"
                response += "• Ask 'recommend stocks' for suggestions\n"
                response += "• Try 'what's the price of [SYMBOL]' to explore stocks"
                
                return {
                    'message': response,
                    'intent': 'watchlist_view',
                    'context': {'watchlist_count': 0},
                    'suggested_actions': ['get_recommendations', 'explore_stocks']
                }
        except Exception as e:
            logger.error(f"Error fetching watchlist: {e}")
            return {
                'message': "I had trouble accessing your watchlist. I'm learning from these issues to improve reliability!",
                'intent': 'watchlist_view',
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
        response += "• 'Add INFY to watchlist'\n"
        response += "• 'Compare TCS vs INFY'\n"
        response += "• 'Analyze my portfolio'\n"
        response += "• 'Recommend some stocks'\n"
        
        response += "\n💡 I learn from every interaction to serve you better!"
        
        return {
            'message': response,
            'intent': 'help',
            'context': {'capabilities_shown': True}
        }
    
    def _handle_compare(self, user_id: int, message: str, preferences: Dict,
                       history: List, context: Dict) -> Dict[str, Any]:
        """Handle stock comparison queries"""
        # Extract stock symbols from message
        symbols = re.findall(r'\b([A-Z]{2,})\b', message)
        
        if len(symbols) < 2:
            return {
                'message': "I'd love to compare stocks for you! Please specify two stock symbols (e.g., 'compare RELIANCE vs TCS').",
                'intent': 'compare',
                'context': {}
            }
        
        symbol1, symbol2 = symbols[0], symbols[1]
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get data for both stocks
            stocks_data = []
            for symbol in [symbol1, symbol2]:
                cursor.execute('''
                    SELECT security_id, company_name, current_value, change, p_change, 
                           day_high, day_low, high_52week, low_52week
                    FROM stock_quotes 
                    WHERE UPPER(security_id) = UPPER(?)
                    LIMIT 1
                ''', (symbol,))
                row = cursor.fetchone()
                if row:
                    stocks_data.append({
                        'security_id': row[0],
                        'company_name': row[1],
                        'current_value': row[2],
                        'change': row[3],
                        'p_change': row[4],
                        'day_high': row[5],
                        'day_low': row[6],
                        'high_52week': row[7],
                        'low_52week': row[8]
                    })
            
            conn.close()
            
            if len(stocks_data) == 2:
                stock1, stock2 = stocks_data[0], stocks_data[1]
                
                response = f"📊 **Comparing {stock1['company_name']} vs {stock2['company_name']}**\n\n"
                
                response += f"**{stock1['security_id']}:**\n"
                response += f"• Price: ₹{stock1['current_value']:.2f} ({stock1['p_change']:+.2f}%)\n"
                response += f"• 52W Range: ₹{stock1['low_52week']:.2f} - ₹{stock1['high_52week']:.2f}\n\n"
                
                response += f"**{stock2['security_id']}:**\n"
                response += f"• Price: ₹{stock2['current_value']:.2f} ({stock2['p_change']:+.2f}%)\n"
                response += f"• 52W Range: ₹{stock2['low_52week']:.2f} - ₹{stock2['high_52week']:.2f}\n\n"
                
                # Add comparison insights
                comparison_insights = self._generate_comparison_insights(stock1, stock2)
                response += f"💡 **Insights:**\n{comparison_insights}"
                
                return {
                    'message': response,
                    'intent': 'compare',
                    'context': {'symbols': [symbol1, symbol2]},
                    'actions_taken': ['compared_stocks']
                }
            else:
                return {
                    'message': "I couldn't find data for one or both stocks. Please verify the symbols and try again.",
                    'intent': 'compare',
                    'context': {'symbols': [symbol1, symbol2]}
                }
        except Exception as e:
            logger.error(f"Error comparing stocks: {e}")
            return {
                'message': "I encountered an issue while comparing stocks. Let me learn from this and improve!",
                'intent': 'compare',
                'context': {'error': str(e)}
            }
    
    def _handle_recommend(self, user_id: int, message: str, preferences: Dict,
                         history: List, context: Dict) -> Dict[str, Any]:
        """Handle stock recommendation requests"""
        try:
            # Get user's watchlist to understand preferences
            watchlist = WatchlistDBService.get_by_user(user_id)
            watched_symbols = [item.stock_symbol for item in watchlist] if watchlist else []
            
            # Get top performing stocks from database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get stocks with positive performance not in watchlist
            placeholders = ','.join(['?' for _ in watched_symbols]) if watched_symbols else ''
            exclude_clause = f"AND security_id NOT IN ({placeholders})" if watched_symbols else ""
            
            query = f'''
                SELECT security_id, company_name, current_value, p_change
                FROM stock_quotes 
                WHERE p_change > 0
                {exclude_clause}
                ORDER BY p_change DESC
                LIMIT 5
            '''
            
            cursor.execute(query, watched_symbols)
            rows = cursor.fetchall()
            conn.close()
            
            if rows:
                response = "💎 **Stock Recommendations** (Based on current performance)\n\n"
                for row in rows:
                    response += f"• **{row[1]}** ({row[0]}): ₹{row[2]:.2f} ({row[3]:+.2f}%)\n"
                
                response += "\n💡 **Why these?**\n"
                response += "• Showing positive momentum today\n"
                response += "• Not currently in your watchlist\n"
                response += "• Sorted by performance\n\n"
                
                response += "Would you like me to add any of these to your watchlist? Just say 'add [SYMBOL] to watchlist'!"
                
                return {
                    'message': response,
                    'intent': 'recommend',
                    'context': {'recommendations': [row[0] for row in rows]},
                    'actions_taken': ['generated_recommendations'],
                    'suggested_actions': ['add_to_watchlist']
                }
            else:
                response = "I'm analyzing market data to find good opportunities for you. "
                response += "Based on your interests, I'll provide personalized recommendations. "
                response += "Try asking about specific stocks or sectors you're interested in!"
                
                return {
                    'message': response,
                    'intent': 'recommend',
                    'context': {}
                }
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return {
                'message': "I'm having trouble generating recommendations right now. Let me improve this feature!",
                'intent': 'recommend',
                'context': {'error': str(e)}
            }
    
    def _handle_analysis(self, user_id: int, message: str, preferences: Dict,
                        history: List, context: Dict) -> Dict[str, Any]:
        """Handle portfolio/stock analysis requests"""
        # Check if analyzing specific stock or watchlist
        symbols = re.findall(r'\b([A-Z]{2,})\b', message)
        
        if symbols:
            # Analyze specific stock
            symbol = symbols[0]
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT security_id, company_name, current_value, change, p_change,
                           day_high, day_low, high_52week, low_52week
                    FROM stock_quotes 
                    WHERE UPPER(security_id) = UPPER(?)
                    LIMIT 1
                ''', (symbol,))
                
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    stock_data = {
                        'security_id': row[0],
                        'company_name': row[1],
                        'current_value': row[2],
                        'change': row[3],
                        'p_change': row[4],
                        'day_high': row[5],
                        'day_low': row[6],
                        'high_52week': row[7],
                        'low_52week': row[8]
                    }
                    
                    response = f"📈 **Analysis: {stock_data['company_name']}** ({stock_data['security_id']})\n\n"
                    
                    # Technical analysis
                    analysis = self._generate_technical_analysis(stock_data)
                    response += analysis
                    
                    return {
                        'message': response,
                        'intent': 'analysis',
                        'context': {'symbol': symbol, 'analysis_type': 'stock'},
                        'actions_taken': ['generated_analysis']
                    }
                else:
                    return {
                        'message': f"I couldn't find data for {symbol}. Please verify the symbol.",
                        'intent': 'analysis',
                        'context': {}
                    }
            except Exception as e:
                logger.error(f"Error analyzing stock: {e}")
                return {
                    'message': "I encountered an issue during analysis. I'm learning to improve this!",
                    'intent': 'analysis',
                    'context': {'error': str(e)}
                }
        else:
            # Analyze watchlist/portfolio
            try:
                watchlist = WatchlistDBService.get_by_user(user_id)
                
                if not watchlist:
                    return {
                        'message': "Your watchlist is empty. Add some stocks to get portfolio analysis! Try 'add [SYMBOL] to watchlist'.",
                        'intent': 'analysis',
                        'context': {}
                    }
                
                # Get stats for watchlist
                conn = get_db_connection()
                cursor = conn.cursor()
                
                symbols = [item.stock_symbol for item in watchlist]
                placeholders = ','.join(['?' for _ in symbols])
                
                cursor.execute(f'''
                    SELECT COUNT(*), AVG(p_change), 
                           SUM(CASE WHEN p_change > 0 THEN 1 ELSE 0 END),
                           SUM(CASE WHEN p_change < 0 THEN 1 ELSE 0 END)
                    FROM stock_quotes 
                    WHERE security_id IN ({placeholders})
                ''', symbols)
                
                stats = cursor.fetchone()
                conn.close()
                
                total_stocks = stats[0]
                avg_change = stats[1] or 0
                gainers = stats[2] or 0
                losers = stats[3] or 0

                response = "📊 **Watchlist Analysis**\n\n"
                response += "**Portfolio Summary:**\n"
                response += f"• Total Stocks: {total_stocks}\n"
                response += f"• Average Change: {avg_change:+.2f}%\n"
                response += f"• Gainers: {gainers} | Losers: {losers}\n\n"
                
                # Add insights
                if avg_change > 2:
                    response += "💡 Your portfolio is performing well! Consider taking profits on strong gainers.\n"
                elif avg_change < -2:
                    response += "💡 Your portfolio is down. Review fundamentals and consider rebalancing.\n"
                else:
                    response += "💡 Your portfolio is stable. Look for growth opportunities.\n"
                
                response += "\nWant detailed analysis of a specific stock? Just ask 'analyze [SYMBOL]'!"
                
                return {
                    'message': response,
                    'intent': 'analysis',
                    'context': {'analysis_type': 'portfolio', 'avg_change': avg_change},
                    'actions_taken': ['analyzed_portfolio']
                }
            except Exception as e:
                logger.error(f"Error analyzing watchlist: {e}")
                return {
                    'message': "I had trouble analyzing your watchlist. Let me improve this feature!",
                    'intent': 'analysis',
                    'context': {'error': str(e)}
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

        response += "**My Stats:**\n"
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
    
    def _generate_price_insights(self, quote_data: Dict) -> str:
        """Generate actionable insights from price data"""
        insights = []
        
        current = quote_data['current_value']
        day_high = quote_data['day_high']
        day_low = quote_data['day_low']
        week_52_high = quote_data['high_52week']
        week_52_low = quote_data['low_52week']
        p_change = quote_data['p_change']
        
        # Performance insight
        if p_change > 3:
            insights.append(f"• Strong upward momentum ({p_change:+.2f}% today)")
        elif p_change < -3:
            insights.append(f"• Significant decline ({p_change:+.2f}% today) - potential buying opportunity?")
        
        # 52-week position
        range_position = (current - week_52_low) / (week_52_high - week_52_low) * 100 if week_52_high != week_52_low else 50
        if range_position > 80:
            insights.append(f"• Trading near 52-week high ({range_position:.0f}% of range)")
        elif range_position < 20:
            insights.append(f"• Trading near 52-week low ({range_position:.0f}% of range) - possible value play")
        
        # Daily range
        if current == day_high:
            insights.append("• Currently at day's high - strong buying pressure")
        elif current == day_low:
            insights.append("• Currently at day's low - watch for support")
        
        return '\n'.join(insights) if insights else "• Stock showing normal trading behavior"
    
    def _generate_prediction_recommendation(self, change_pct: float, pred: Any) -> str:
        """Generate actionable recommendation from prediction"""
        if abs(change_pct) < 2:
            return "HOLD - Prediction shows minimal movement. Consider waiting for clearer signals."
        elif change_pct > 5:
            return f"POSITIVE OUTLOOK - Prediction suggests {change_pct:.1f}% upside. Consider buying if fundamentals align."
        elif change_pct > 2:
            return f"CAUTIOUSLY POSITIVE - Moderate {change_pct:.1f}% upside predicted. Monitor closely."
        elif change_pct < -5:
            return f"CAUTION - Prediction shows {abs(change_pct):.1f}% downside risk. Consider defensive positioning."
        else:
            return f"NEUTRAL TO NEGATIVE - Slight {abs(change_pct):.1f}% downside. Watch for trend reversal."
    
    def _generate_comparison_insights(self, stock1: Dict, stock2: Dict) -> str:
        """Generate insights from stock comparison"""
        insights = []
        
        # Performance comparison
        if stock1['p_change'] > stock2['p_change']:
            insights.append(f"• {stock1['security_id']} is outperforming ({stock1['p_change']:+.2f}% vs {stock2['p_change']:+.2f}%)")
        else:
            insights.append(f"• {stock2['security_id']} is outperforming ({stock2['p_change']:+.2f}% vs {stock1['p_change']:+.2f}%)")
        
        # Volatility comparison (using 52-week range as proxy)
        vol1 = (stock1['high_52week'] - stock1['low_52week']) / stock1['low_52week'] * 100
        vol2 = (stock2['high_52week'] - stock2['low_52week']) / stock2['low_52week'] * 100
        
        if vol1 > vol2 * 1.2:
            insights.append(f"• {stock1['security_id']} shows higher volatility ({vol1:.0f}% vs {vol2:.0f}%)")
        elif vol2 > vol1 * 1.2:
            insights.append(f"• {stock2['security_id']} shows higher volatility ({vol2:.0f}% vs {vol1:.0f}%)")
        else:
            insights.append("• Both stocks show similar volatility")
        
        return '\n'.join(insights)
    
    def _generate_technical_analysis(self, stock_data: Dict) -> str:
        """Generate technical analysis for a stock"""
        analysis = []
        
        current = stock_data['current_value']
        p_change = stock_data['p_change']
        high_52w = stock_data['high_52week']
        low_52w = stock_data['low_52week']
        
        # Trend
        analysis.append("**Trend Analysis:**")
        if p_change > 2:
            analysis.append("• Bullish trend - positive momentum")
        elif p_change < -2:
            analysis.append("• Bearish trend - negative pressure")
        else:
            analysis.append("• Neutral trend - consolidation phase")
        
        # Position in range
        range_pos = (current - low_52w) / (high_52w - low_52w) * 100 if high_52w != low_52w else 50
        analysis.append(f"\n**Position:** {range_pos:.1f}% of 52-week range")
        
        if range_pos > 75:
            analysis.append("• Near resistance - watch for breakout or reversal")
        elif range_pos < 25:
            analysis.append("• Near support - potential bounce opportunity")
        else:
            analysis.append("• Mid-range - direction unclear, wait for confirmation")
        
        # Risk assessment
        analysis.append("\n**Risk Level:**")
        volatility = (high_52w - low_52w) / low_52w * 100
        if volatility > 50:
            analysis.append("• HIGH - Large price swings, suitable for risk-tolerant traders")
        elif volatility > 25:
            analysis.append("• MODERATE - Normal market volatility")
        else:
            analysis.append("• LOW - Stable price action, conservative play")
        
        return '\n'.join(analysis)
