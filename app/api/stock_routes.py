import logging
from flask import Blueprint, request, jsonify
from app.db.session_manager import get_session_manager
from app.utils.yfinance_utils import search_companies_by_name, get_quote_by_company_name

stock_bp = Blueprint('stock', __name__, url_prefix='/api/stocks')


@stock_bp.route('suggestions', methods=['GET'])
def get_stock_suggestions():
    """Get stock suggestions based on query parameter 'q'"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400

    try:
        db = get_session_manager()
        rows = db.fetch_all(
            'SELECT company_name, scrip_code FROM STK WHERE company_name LIKE ? ORDER BY company_name ASC LIMIT 10',
            (f'%{query}%',),
        )
        suggestions = [{'company_name': row['company_name'], 'scrip_code': row['scrip_code']} for row in rows]
        logging.info(suggestions)
        return suggestions, 200

    except Exception as e:
        logging.error(f"Error fetching stock suggestions: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


@stock_bp.route('/search', methods=['GET'])
def search_stocks():
    """
    Search for companies by name using yfinance Search API.

    Query parameters:
    - q (required): Company name to search for
    - max_results (optional): Maximum number of results (default: 10)
    - indian_only (optional): Filter to Indian stocks only (default: true)

    Returns:
        List of search results with symbol, name, exchange, type, etc.
    """
    company_name = request.args.get('q', '').strip()
    if not company_name:
        return jsonify({'error': 'Query parameter "q" (company name) is required'}), 400

    try:
        max_results = request.args.get('max_results', 10, type=int)
        indian_only = request.args.get('indian_only', 'true').lower() == 'true'

        # Validate parameters
        if max_results < 1 or max_results > 50:
            return jsonify({'error': 'max_results must be between 1 and 50'}), 400

        results = search_companies_by_name(
            company_name=company_name,
            max_results=max_results,
            indian_only=indian_only,
            max_retries=3,
            delay=1
        )

        return jsonify({
            'query': company_name,
            'results': results,
            'count': len(results)
        }), 200

    except Exception as e:
        logging.error(f"Error searching for companies: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


@stock_bp.route('/quote-by-name', methods=['GET'])
def get_quote_by_name():
    """
    Get stock quote by company name using yfinance.
    The function automatically searches for the company and returns the quote
    in BSE-compatible format.

    Query parameters:
    - q (required): Company name to search for
    - max_search_results (optional): Maximum search results to try (default: 5)

    Returns:
        Stock quote in BSE-compatible format with search match information
    """
    company_name = request.args.get('q', '').strip()
    if not company_name:
        return jsonify({'error': 'Query parameter "q" (company name) is required'}), 400

    try:
        max_search_results = request.args.get('max_search_results', 5, type=int)

        # Validate parameters
        if max_search_results < 1 or max_search_results > 20:
            return jsonify({'error': 'max_search_results must be between 1 and 20'}), 400

        quote = get_quote_by_company_name(
            company_name=company_name,
            max_search_results=max_search_results,
            max_retries=3,
            delay=1
        )

        if quote:
            return jsonify({
                'success': True,
                'quote': quote
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': f'Could not find quote for company: {company_name}'
            }), 404

    except Exception as e:
        logging.error(f"Error fetching quote by company name: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


@stock_bp.route('/list', methods=['GET'])
def list_stocks():
    """
    List stocks with pagination and sorting.
    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50)
    - sort_by: Column to sort by (default: company_name)
    - sort_order: Sort order (asc or desc, default: asc)
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    sort_by = request.args.get('sort_by', 'company_name')
    sort_order = request.args.get('sort_order', 'asc')

    # Pagination limits
    per_page = min(max(per_page, 10), 100)  # Between 10 and 100
    page = max(page, 1)

    # Allowed sort columns - using a mapping to prevent SQL injection
    allowed_sort_columns = {
        'company_name': 'company_name',
        'security_id': 'security_id',
        'current_value': 'current_value',
        'change': 'change',
        'p_change': 'p_change',
        'day_high': 'day_high',
        'day_low': 'day_low',
        'previous_close': 'previous_close',
        'industry': 'industry',
        'updated_on': 'updated_on'
    }

    # Validate and sanitize sort column
    if sort_by not in allowed_sort_columns:
        sort_by = 'company_name'
    else:
        sort_by = allowed_sort_columns[sort_by]

    # Validate and sanitize sort order
    if sort_order.lower() not in ['asc', 'desc']:
        sort_order = 'ASC'
    else:
        sort_order = 'ASC' if sort_order.lower() == 'asc' else 'DESC'

    try:
        db = get_session_manager()
        total_row = db.fetch_one('SELECT COUNT(*) as count FROM stock_quotes')
        total_count = total_row['count'] if total_row else 0

        offset = (page - 1) * per_page

        # sort_by and sort_order are validated above against a whitelist
        rows = db.fetch_all(
            f'''SELECT
                id, company_name, security_id, scrip_code, current_value,
                change, p_change, day_high, day_low, previous_close,
                previous_open, high_52week, low_52week, industry,
                market_cap_full, total_traded_value, updated_on, stock_status
            FROM stock_quotes
            ORDER BY {sort_by} {sort_order}
            LIMIT ? OFFSET ?''',
            (per_page, offset),
        )

        stocks = [
            {
                'id': row['id'],
                'company_name': row['company_name'],
                'security_id': row['security_id'],
                'scrip_code': row['scrip_code'],
                'current_value': row['current_value'],
                'change': row['change'],
                'p_change': row['p_change'],
                'day_high': row['day_high'],
                'day_low': row['day_low'],
                'previous_close': row['previous_close'],
                'previous_open': row['previous_open'],
                'week_52_high': row['high_52week'],
                'week_52_low': row['low_52week'],
                'industry': row['industry'],
                'market_cap_full': row['market_cap_full'],
                'total_traded_value': row['total_traded_value'],
                'updated_on': row['updated_on'],
                'stock_status': row['stock_status'],
            }
            for row in rows
        ]

        total_pages = (total_count + per_page - 1) // per_page

        return jsonify({
            'stocks': stocks,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages
            },
            'sorting': {
                'sort_by': sort_by,
                'sort_order': sort_order
            }
        }), 200

    except Exception as e:
        logging.error(f"Error listing stocks: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


@stock_bp.route('/<security_id>', methods=['GET'])
def get_stock_details(security_id):
    """Get detailed information for a specific stock."""
    try:
        db = get_session_manager()
        row = db.fetch_one(
            '''SELECT
                id, company_name, security_id, scrip_code, current_value,
                change, p_change, day_high, day_low, previous_close,
                previous_open, high_52week, low_52week, industry,
                market_cap_full, total_traded_value, updated_on, stock_status,
                face_value, weighted_avg_price, total_traded_quantity,
                two_week_avg_quantity, market_cap_free_float
            FROM stock_quotes
            WHERE security_id = ?''',
            (security_id,),
        )

        if not row:
            return jsonify({'error': 'Stock not found'}), 404

        stock = {
            'id': row['id'],
            'company_name': row['company_name'],
            'security_id': row['security_id'],
            'scrip_code': row['scrip_code'],
            'current_value': row['current_value'],
            'change': row['change'],
            'p_change': row['p_change'],
            'day_high': row['day_high'],
            'day_low': row['day_low'],
            'previous_close': row['previous_close'],
            'previous_open': row['previous_open'],
            'week_52_high': row['high_52week'],
            'week_52_low': row['low_52week'],
            'industry': row['industry'],
            'market_cap_full': row['market_cap_full'],
            'total_traded_value': row['total_traded_value'],
            'updated_on': row['updated_on'],
            'stock_status': row['stock_status'],
            'face_value': row['face_value'],
            'weighted_avg_price': row['weighted_avg_price'],
            'total_traded_quantity': row['total_traded_quantity'],
            'two_week_avg_quantity': row['two_week_avg_quantity'],
            'market_cap_free_float': row['market_cap_free_float'],
        }

        return jsonify(stock), 200

    except Exception as e:
        logging.error(f"Error getting stock details: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500
