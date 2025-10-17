"""
Price streaming API routes for real-time stock price updates
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required

from app.services.price_streamer import price_streamer

price_stream_bp = Blueprint('price_stream', __name__, url_prefix='/api/price_stream')


@price_stream_bp.route('/start', methods=['POST'])
@login_required
def start_price_streaming():
    """Start price streaming for specified symbols"""
    data = request.get_json()
    symbols = data.get('symbols', [])
    
    for symbol in symbols:
        price_streamer.add_symbol(symbol)
    
    if not price_streamer.streaming:
        price_streamer.start_streaming()
    
    return jsonify({
        'success': True,
        'message': f'Started streaming for {len(symbols)} symbols',
        'symbols': symbols
    }), 200


@price_stream_bp.route('/stop', methods=['POST'])
@login_required
def stop_price_streaming():
    """Stop price streaming for specified symbols"""
    data = request.get_json()
    symbols = data.get('symbols', [])
    
    for symbol in symbols:
        price_streamer.remove_symbol(symbol)
    
    return jsonify({
        'success': True,
        'message': f'Stopped streaming for {len(symbols)} symbols',
        'symbols': symbols
    }), 200


@price_stream_bp.route('/status', methods=['GET'])
@login_required
def price_streaming_status():
    """Get price streaming status"""
    return jsonify({
        'streaming': price_streamer.streaming,
        'watched_symbols': price_streamer.get_watched_symbols(),
        'update_interval': price_streamer.update_interval
    }), 200


@price_stream_bp.route('/price/<symbol>', methods=['GET'])
@login_required
def get_live_price(symbol):
    """Get live price for a specific symbol"""
    price_data = price_streamer.fetch_price_once(symbol)
    
    if price_data:
        return jsonify({
            'success': True,
            'data': price_data
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to fetch price'
        }), 404
