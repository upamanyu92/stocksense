from typing import Dict, Any
from app.models.gemini_model import predict_with_details


def ask_advisor(user_context: Dict[str, Any], question: str) -> Dict[str, Any]:
    # High-level wrapper to provide personalized advice using Gemini while keeping context
    # For now call predict_with_details as a simple proxy
    # Real implementation would craft prompts with user_context and question
    try:
        res = predict_with_details(user_context.get('symbol', ''))
        return {'answer': f"Proxy answer for {question}", 'details': res}
    except Exception as e:
        return {'answer': 'Error', 'error': str(e)}
