import sqlite3
import logging
from flask import Blueprint, request, jsonify
from app.utils.util import get_db_connection

stock_bp = Blueprint('stock', __name__)

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
