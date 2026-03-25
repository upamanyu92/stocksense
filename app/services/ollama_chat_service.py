"""
Ollama LLM integration for chat agent - handles natural language processing with local LLM.
Falls back to GitHub Copilot / GitHub Models API when Ollama is unavailable.
"""
import asyncio
import concurrent.futures
import logging
import json
from typing import Dict, Any, Optional

import requests.exceptions

from app.models.ollama_model import _call_ollama_with_retry

logger = logging.getLogger(__name__)


def _run_async(coro):
    """
    Run an async coroutine from a synchronous context.

    Uses asyncio.run() when no event loop is active; otherwise submits
    the coroutine to a background thread to avoid 'cannot be called from
    a running event loop' errors (e.g. when Flask-SocketIO is active).
    """
    try:
        asyncio.get_running_loop()
        # A loop is already running – execute in a dedicated thread
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No running loop – safe to call asyncio.run() directly
        return asyncio.run(coro)


class OllamaChatService:
    """Service for integrating Ollama LLM with chat agent"""

    SYSTEM_PROMPT = """You are StockSense AI - a helpful assistant for stock market analysis and predictions.

Your role:
- Help users understand stock market data
- Provide stock price information and predictions
- Assist with watchlist management (add/remove stocks)
- Help run predictions on single stocks or groups
- Display current and predicted values for stocks
- Answer questions about NSE securities

Your capabilities:
- Extract stock symbols from user messages
- Understand intents: check_price, predict, add_watchlist, remove_watchlist, run_prediction, show_values, list_stocks
- Provide clear, concise responses
- Remember context from previous messages

Always:
- Be helpful and professional
- Admit when you don't have enough information
- Suggest actions the user can take
- Keep responses concise and actionable

When user asks about:
- Stock prices: Extract symbol and confirm what they want
- Predictions: Confirm if for single stock or watchlist, then suggest running prediction
- Watchlist: Offer to add/remove/view
- NSE stocks: Offer to show available stocks or search specific ones"""

    def __init__(self):
        self.conversation_history = []

    def process_user_message(self,
                            user_message: str,
                            context: Optional[Dict[str, Any]] = None,
                            conversation_history: Optional[list] = None) -> Dict[str, Any]:
        """
        Process user message through Ollama LLM with context awareness.

        Args:
            user_message: The user's message
            context: Additional context (stocks, watchlist, etc.)
            conversation_history: Previous messages in conversation

        Returns:
            Dictionary with response and extracted intent/entities
        """
        try:
            # Build context string
            context_str = self._build_context_string(context, conversation_history)

            # Build the prompt
            prompt = self._build_chat_prompt(user_message, context_str)

            # Get response from Ollama
            response = _call_ollama_with_retry(prompt, max_retries=2)
            response_text = response.get('response', '')

            # Parse the response to extract intent and action
            intent, action, entities = self._parse_response(response_text, user_message)

            return {
                'response': response_text.strip(),
                'intent': intent,
                'action': action,
                'entities': entities,
                'success': True
            }
        except (requests.exceptions.RequestException, OSError, TimeoutError, RuntimeError, Exception) as e:
            # Catches connectivity failures (ConnectionError, Timeout) and the generic Exception
            # raised by _call_ollama_with_retry when Ollama returns a non-200 HTTP status.
            logger.warning(f"Ollama chat processing failed ({e}); attempting GitHub Copilot fallback")
            try:
                return self._process_with_copilot(user_message, context, conversation_history)
            except Exception as copilot_exc:
                logger.error(f"GitHub Copilot fallback also failed: {copilot_exc}")
                return {
                    'response': "I apologize, but I encountered an error processing your request. Please try again.",
                    'intent': 'error',
                    'action': None,
                    'entities': {},
                    'success': False
                }

    def _process_with_copilot(self,
                              user_message: str,
                              context: Optional[Dict[str, Any]] = None,
                              conversation_history: Optional[list] = None) -> Dict[str, Any]:
        """
        Fallback: process the user message via the GitHub Copilot / GitHub Models API
        when Ollama is unavailable (e.g. running in Docker without a local Ollama service).

        Requires:
            - GITHUB_TOKEN env var set to a valid personal-access-token or Copilot token
            - ``openai`` package installed (``pip install openai>=1.0.0``)
        """
        # Late import to break the circular dependency:
        # copilot_agent → (tools) → services, and OllamaChatService ← chat_agent ← chat_routes
        from app.agents.copilot_agent import CopilotClient

        client = CopilotClient()
        if not client.is_available():
            raise RuntimeError(
                "GitHub Copilot API is unavailable: GITHUB_TOKEN not set or openai package missing"
            )

        context_str = self._build_context_string(context, conversation_history)
        full_message = f"Context:\n{context_str}\n\nUser: {user_message}"

        async def _run_session() -> str:
            session = await client.create_session(
                system_prompt=self.SYSTEM_PROMPT,
                tools=[],
                tool_handlers={},
            )
            return await session.run(full_message)

        response_text = _run_async(_run_session())
        intent, action, entities = self._parse_response(response_text, user_message)

        logger.info("GitHub Copilot fallback succeeded for chat message")
        return {
            'response': response_text.strip(),
            'intent': intent,
            'action': action,
            'entities': entities,
            'success': True,
        }

    def _build_context_string(self,
                             context: Optional[Dict] = None,
                             history: Optional[list] = None) -> str:
        """Build context string for the LLM"""
        context_parts = []

        if history and len(history) > 0:
            context_parts.append("Recent conversation:")
            for msg in history[-3:]:  # Last 3 messages
                context_parts.append(f"- User: {msg.get('user_message', '')}")
                context_parts.append(f"  Assistant: {msg.get('response', '')}")

        if context:
            if context.get('current_stocks'):
                context_parts.append(f"Current stocks being viewed: {', '.join(context['current_stocks'])}")

            if context.get('watchlist'):
                context_parts.append(f"User's watchlist: {', '.join(context['watchlist'])}")

            if context.get('recent_predictions'):
                context_parts.append(f"Recent predictions available for: {', '.join(context['recent_predictions'])}")

        return "\n".join(context_parts) if context_parts else "Starting fresh conversation"

    def _build_chat_prompt(self, user_message: str, context_str: str) -> str:
        """Build the prompt for Ollama"""
        return f"""{self.SYSTEM_PROMPT}

Current Context:
{context_str}

User Message: {user_message}

Please respond naturally as the StockSense AI assistant. If the user is asking about:
1. Stock prices - extract the symbol and ask for clarification if needed
2. Predictions - determine if for single stock or watchlist group
3. Watchlist management - confirm the action (add/remove/view)
4. NSE stocks - offer to search or list available stocks
5. Current/predicted values - identify which stocks and prepare data display

Always include what action you're about to take or suggest next steps.

Response:"""

    def _parse_response(self, response: str, user_message: str) -> tuple:
        """
        Parse the LLM response to extract intent and action.

        Returns:
            Tuple of (intent, action, entities)
        """
        response_lower = response.lower()

        # Detect intent
        intent = 'general'
        action = None
        entities = {}

        # Stock price intent
        if any(word in response_lower for word in ['stock price', 'current price', 'quote', 'value']):
            intent = 'check_price'
            action = 'get_stock_price'

        # Prediction intent
        elif any(word in response_lower for word in ['predict', 'forecast', 'run prediction']):
            intent = 'predict'
            action = 'run_prediction'
            # Check if for watchlist or single stock
            if 'watchlist' in response_lower or 'group' in response_lower or 'all' in response_lower:
                entities['prediction_scope'] = 'watchlist'
            else:
                entities['prediction_scope'] = 'single'

        # Watchlist intent
        elif any(word in response_lower for word in ['watchlist', 'watch', 'track', 'follow']):
            intent = 'watchlist'
            if 'add' in response_lower or 'adding' in response_lower:
                action = 'add_watchlist'
            elif 'remove' in response_lower or 'delete' in response_lower:
                action = 'remove_watchlist'
            else:
                action = 'view_watchlist'

        # Values display intent
        elif any(word in response_lower for word in ['current value', 'predicted value', 'show', 'display']):
            intent = 'show_values'
            action = 'display_stock_values'

        # List stocks intent
        elif any(word in response_lower for word in ['available stocks', 'nse stocks', 'securities', 'list stocks']):
            intent = 'list_stocks'
            action = 'list_available_stocks'

        # Extract stock symbols from both response and original message
        import re
        symbols = re.findall(r'\b([A-Z]{2,})\b', response + ' ' + user_message)
        if symbols:
            entities['symbols'] = list(set(symbols))  # Remove duplicates

        return intent, action, entities

