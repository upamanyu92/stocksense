"""
Watchlist management API routes.
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.services.auth_service import WatchlistService

watchlist_bp = Blueprint('watchlist', __name__, url_prefix='/api/watchlist')


@watchlist_bp.route('/', methods=['GET'])
@login_required
def get_watchlist():
    """Get user's watchlist"""
    try:
        watchlist = WatchlistService.get_watchlist(current_user.id)
        return jsonify({
            'success': True,
            'watchlist': watchlist
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@watchlist_bp.route('/add', methods=['POST'])
@login_required
def add_to_watchlist():
    """Add stock to watchlist"""
    data = request.get_json()
    stock_symbol = data.get('stock_symbol')
    company_name = data.get('company_name')
    
    if not stock_symbol:
        return jsonify({
            'success': False,
            'error': 'Stock symbol is required'
        }), 400
    
    success = WatchlistService.add_to_watchlist(
        current_user.id,
        stock_symbol,
        company_name
    )
    
    if success:
        return jsonify({
            'success': True,
            'message': 'Stock added to watchlist'
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to add stock to watchlist'
        }), 500


@watchlist_bp.route('/remove', methods=['POST'])
@login_required
def remove_from_watchlist():
    """Remove stock from watchlist"""
    data = request.get_json()
    stock_symbol = data.get('stock_symbol')
    
    if not stock_symbol:
        return jsonify({
            'success': False,
            'error': 'Stock symbol is required'
        }), 400
    
    success = WatchlistService.remove_from_watchlist(
        current_user.id,
        stock_symbol
    )
    
    if success:
        return jsonify({
            'success': True,
            'message': 'Stock removed from watchlist'
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to remove stock from watchlist'
        }), 500


@watchlist_bp.route('/reorder', methods=['POST'])
@login_required
def reorder_watchlist():
    """Update display order of stocks in watchlist"""
    data = request.get_json()
    items = data.get('items', [])
    
    try:
        for item in items:
            WatchlistService.update_display_order(
                current_user.id,
                item['stock_symbol'],
                item['order']
            )
        
        return jsonify({
            'success': True,
            'message': 'Watchlist order updated'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def get_user_watchlist_stocks(user_id):
    """Return a list of stock objects in the user's watchlist for internal use."""
    return WatchlistService.get_watchlist(user_id)
