"""
Stock-related API routes.
"""
import logging
from flask import Blueprint, jsonify

from app.db.db_executor import fetch_quotes

stock_bp = Blueprint('stock', __name__)

logger = logging.getLogger(__name__)


@stock_bp.route('/search_quote/<company_name>', methods=['GET'])
def search_quote(company_name):
    """Search for stock quotes by company name."""
    logger.info(f"Searching for quote: {company_name}")
    data = fetch_quotes(company_name)
    
    if not data or "quotes" not in data or len(data["quotes"]) == 0:
        return jsonify({"quotes": [], "message": "No data found"}), 404
    
    logger.info(f"Found {len(data['quotes'])} quotes for {company_name}")
    return jsonify(data["quotes"])


@stock_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker and monitoring."""
    return jsonify({"status": "healthy", "service": "stocksense"}), 200
