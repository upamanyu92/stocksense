from flask import Blueprint, jsonify
from flask_login import login_required

from app.services.price_streamer import price_streamer

price_bp = Blueprint('price', __name__, url_prefix='/api/price')

@price_bp.route('/<symbol>', methods=['GET'])
@login_required
def get_live_price(symbol):
    """Get live price for a specific symbol"""
    price_data = price_streamer.fetch_price_once(symbol)
    if price_data:
        return jsonify({'success': True, 'data': price_data}), 200
    else:
        return jsonify({'success': False, 'error': 'Failed to fetch price'}), 404

