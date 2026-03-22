import logging
from typing import Any, Dict, List, Optional

from flask import Blueprint, request, jsonify

from app.utils.util import get_db_connection
from app.utils.yfinance_utils import get_quote_by_company_name, search_companies_by_name

stock_bp = Blueprint('stock', __name__, url_prefix='/api/stocks')


def _normalize_quote(quote: Any) -> Optional[Dict[str, Any]]:
    """Return a consistent, snake_case quote payload for UI consumption."""
    if not quote:
        return None

    # Support sqlite Row and plain dict objects
    data = dict(quote)

    def pick(*keys, default=None):
        for key in keys:
            if key in data and data[key] not in (None, ''):
                return data[key]
        return default

    security_id = pick('security_id', 'securityID', 'scrip_code', 'scripCode', 'stock_symbol', 'symbol')
    scrip_code = pick('scrip_code', 'scripCode', 'security_id', 'securityID', 'stock_symbol', 'symbol')

    return {
        'company_name': pick('company_name', 'companyName', 'name', default=security_id),
        'security_id': security_id,
        'scrip_code': scrip_code,
        'stock_symbol': pick('stock_symbol', 'symbol', default=security_id or scrip_code),
        'current_value': pick('current_value', 'currentValue', 'current_price', 'currentPrice', 'lastPrice'),
        'change': pick('change', 'regularMarketChange'),
        'p_change': pick('p_change', 'pChange', 'regularMarketChangePercent'),
        'day_high': pick('day_high', 'dayHigh'),
        'day_low': pick('day_low', 'dayLow'),
        'industry': pick('industry', 'sector'),
        'stock_status': pick('stock_status', 'status'),
        'updated_on': pick('updated_on', 'updatedOn'),
    }


def _find_local_quote(identifier: str) -> Optional[Dict[str, Any]]:
    """Try to resolve a quote from the local stock_quotes table."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        like_value = f'%{identifier}%'
        cursor.execute(
            '''
            SELECT company_name, security_id, scrip_code, current_value, change, p_change,
                   day_high, day_low, industry, stock_status, updated_on
            FROM stock_quotes
            WHERE company_name LIKE ? OR security_id LIKE ? OR scrip_code LIKE ?
            ORDER BY company_name ASC
            LIMIT 1
            ''',
            (like_value, like_value, like_value)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return _normalize_quote(row)
    except Exception as exc:
        logging.error("Error fetching local quote: %s", exc, exc_info=True)
    return None


def _collect_suggestions(cursor, query: str, limit: int) -> List[Dict[str, str]]:
    """Return suggestions from stock_quotes and STK with graceful fallbacks."""
    like_value = f'%{query}%'

    # Primary: stock_quotes (already populated by ETL)
    cursor.execute(
        '''
        SELECT company_name, security_id, scrip_code
        FROM stock_quotes
        WHERE company_name LIKE ? OR security_id LIKE ? OR scrip_code LIKE ?
        ORDER BY company_name ASC
        LIMIT ?
        ''',
        (like_value, like_value, like_value, limit)
    )
    rows = cursor.fetchall()
    if rows:
        return [
            {
                'company_name': row['company_name'],
                'scrip_code': row['security_id'] or row['scrip_code'],
                'security_id': row['security_id']
            }
            for row in rows
        ]

    # Fallback: STK master table
    cursor.execute(
        '''
        SELECT company_name, scrip_code
        FROM STK
        WHERE company_name LIKE ? OR scrip_code LIKE ?
        ORDER BY company_name ASC
        LIMIT ?
        ''',
        (like_value, like_value, limit)
    )
    rows = cursor.fetchall()
    if rows:
        return [
            {
                'company_name': row['company_name'],
                'scrip_code': row['scrip_code'],
                'security_id': row['scrip_code']
            }
            for row in rows
        ]

    return []


@stock_bp.route('suggestions', methods=['GET'])
def get_stock_suggestions():
    """Get stock suggestions based on query parameter 'q'."""
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)
    limit = max(1, min(limit, 25))  # prevent abuse

    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400

    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row  # ensure named access
        cursor = conn.cursor()

        suggestions = _collect_suggestions(cursor, query, limit)
        conn.close()

        return jsonify({'suggestions': suggestions, 'count': len(suggestions)}), 200

    except Exception as e:
        logging.error(f"Error fetching stock suggestions: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


@stock_bp.route('/search', methods=['GET'])
def search_stocks():
    """Search companies by name using local data first, then external APIs."""
    company_name = request.args.get('q', '').strip()
    if not company_name:
        return jsonify({'error': 'Query parameter "q" (company name) is required'}), 400

    try:
        max_results = request.args.get('max_results', 10, type=int)
        indian_only = request.args.get('indian_only', 'true').lower() == 'true'

        # Validate parameters
        if max_results < 1 or max_results > 50:
            return jsonify({'error': 'max_results must be between 1 and 50'}), 400

        # First, try local DB to avoid API latency and missing results
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        local_matches = _collect_suggestions(cursor, company_name, max_results)
        conn.close()

        results = local_matches

        # Fallback to external search if nothing local
        if not results:
            api_results = search_companies_by_name(
                company_name=company_name,
                max_results=max_results,
                indian_only=indian_only,
                max_retries=3,
                delay=1
            )
            results = [
                {
                    'company_name': r.get('name') or r.get('company_name'),
                    'scrip_code': r.get('symbol'),
                    'security_id': r.get('symbol'),
                    'exchange': r.get('exchange'),
                    'type': r.get('type')
                }
                for r in api_results
            ]

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
        sort_order = 'asc'
    else:
        sort_order = 'ASC' if sort_order.lower() == 'asc' else 'DESC'

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get total count
        cursor.execute('SELECT COUNT(*) FROM stock_quotes')
        total_count = cursor.fetchone()[0]

        # Calculate offset
        offset = (page - 1) * per_page

        # Build query with safe sorting using validated column and order
        # sort_by and sort_order are now guaranteed to be safe values from our whitelist
        # Note: Using high_52week and low_52week as per schema.sql
        query = f'''
            SELECT
                id, company_name, security_id, scrip_code, current_value,
                change, p_change, day_high, day_low, previous_close,
                previous_open, high_52week, low_52week, industry,
                market_cap_full, total_traded_value, updated_on, stock_status
            FROM stock_quotes
            ORDER BY {sort_by} {sort_order}
            LIMIT ? OFFSET ?
        '''

        cursor.execute(query, (per_page, offset))
        rows = cursor.fetchall()
        conn.close()

        # Convert rows to list of dictionaries
        stocks = []
        for row in rows:
            stocks.append({
                'id': row[0],
                'company_name': row[1],
                'security_id': row[2],
                'scrip_code': row[3],
                'current_value': row[4],
                'change': row[5],
                'p_change': row[6],
                'day_high': row[7],
                'day_low': row[8],
                'previous_close': row[9],
                'previous_open': row[10],
                'week_52_high': row[11],
                'week_52_low': row[12],
                'industry': row[13],
                'market_cap_full': row[14],
                'total_traded_value': row[15],
                'updated_on': row[16],
                'stock_status': row[17]
            })

        # Calculate pagination metadata
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
        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
            SELECT
                id, company_name, security_id, scrip_code, current_value,
                change, p_change, day_high, day_low, previous_close,
                previous_open, high_52week, low_52week, industry,
                market_cap_full, total_traded_value, updated_on, stock_status,
                face_value, weighted_avg_price, total_traded_quantity,
                two_week_avg_quantity, market_cap_free_float
            FROM stock_quotes
            WHERE security_id = ?
        '''

        cursor.execute(query, (security_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({'error': 'Stock not found'}), 404

        stock = {
            'id': row[0],
            'company_name': row[1],
            'security_id': row[2],
            'scrip_code': row[3],
            'current_value': row[4],
            'change': row[5],
            'p_change': row[6],
            'day_high': row[7],
            'day_low': row[8],
            'previous_close': row[9],
            'previous_open': row[10],
            'week_52_high': row[11],
            'week_52_low': row[12],
            'industry': row[13],
            'market_cap_full': row[14],
            'total_traded_value': row[15],
            'updated_on': row[16],
            'stock_status': row[17],
            'face_value': row[18],
            'weighted_avg_price': row[19],
            'total_traded_quantity': row[20],
            'two_week_avg_quantity': row[21],
            'market_cap_free_float': row[22]
        }

        return jsonify(stock), 200

    except Exception as e:
        logging.error(f"Error getting stock details: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500
