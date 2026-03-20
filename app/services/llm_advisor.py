from typing import Dict, Any
from app.models.llm_factory import LLMFactory


def ask_advisor(user_context: Dict[str, Any], question: str) -> Dict[str, Any]:
    """High-level wrapper that provides personalised stock advice via the LLM factory.

    Routes to Ollama in dev mode and to the configured cloud LLM in production.
    """
    symbol = user_context.get('symbol', '')
    try:
        prediction_result = LLMFactory.predict_with_details(symbol)
        return {
            'answer': f"Proxy answer for {question}",
            'details': prediction_result,
            'backend': LLMFactory.active_backend(),
        }
    except Exception as e:
        return {'answer': 'Error', 'error': str(e)}
