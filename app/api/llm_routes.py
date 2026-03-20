from flask import Blueprint, request, jsonify
from app.services.llm_advisor import ask_advisor

llm_bp = Blueprint('llm', __name__, url_prefix='/api/llm')

@llm_bp.route('/ask', methods=['POST'])
def ask():
    data = request.json or {}
    ctx = data.get('context', {})
    q = data.get('question', '')
    res = ask_advisor(ctx, q)
    return jsonify(res)
