from flask import Blueprint, request, jsonify
from app.services.llm_advisor import ask_advisor

llm_bp = Blueprint('llm', __name__, url_prefix='/api/llm')

@llm_bp.route('/ask', methods=['POST'])
def ask():
    data = request.json or {}
    user_context = data.get('context', {})
    user_question = data.get('question', '')
    advisor_response = ask_advisor(user_context, user_question)
    return jsonify(advisor_response)
