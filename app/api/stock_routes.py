"""
Stock quotes API routes for stock search and data fetching operations
"""
import concurrent.futures
import logging
import queue

from flask import Blueprint, jsonify, Response

from app.db.db_executor import fetch_quotes, data_retriever_executor

stock_bp = Blueprint('stock', __name__, url_prefix='/api/stocks')

# Queue for fetch quotes status updates
fetch_quotes_status_queue = queue.Queue()


@stock_bp.route('/search/<company_name>', methods=['GET'])
def search_quote(company_name):
    """Search for stock quotes by company name"""
    logging.info(f"Searching for quote: {company_name}")
    data = fetch_quotes(company_name)
    logging.info(data)

    if not data or "quotes" not in data or len(data["quotes"]) == 0:
        return jsonify({"quotes": [], "message": "No data found"}), 404
    else:
        logging.info(f"Found {len(data['quotes'])} quotes")
        return jsonify(data["quotes"])


@stock_bp.route('/fetch', methods=['POST'])
def fetch_stock_quotes():
    """Fetch and update stock quotes from external source"""
    logging.info("Starting stock quotes fetching process")
    fetch_quotes_status_queue.put("Starting stock quotes fetching process...")
    logging.info("fetch_stock_quotes endpoint triggered")
    fetch_quotes_status_queue.put("fetch_stock_quotes endpoint triggered")

    stock_list = fetch_quotes("")  # Fetch all stocks
    results = []

    def retrieve_and_store(quote):
        try:
            fetch_quotes_status_queue.put(f"Processing stock: {getattr(quote, 'company_name', str(quote))}")
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as single_executor:
                future = single_executor.submit(data_retriever_executor, fetch_quotes_status_queue, 1)
                _ = future.result(timeout=30)  # Result not used, just ensuring completion
            fetch_quotes_status_queue.put(f"Done: {getattr(quote, 'company_name', str(quote))}")
            return {'stock': getattr(quote, 'company_name', str(quote)), 'status': 'done'}
        except concurrent.futures.TimeoutError:
            fetch_quotes_status_queue.put(f"Timeout: {getattr(quote, 'company_name', str(quote))}")
            return {'stock': getattr(quote, 'company_name', str(quote)), 'status': 'timeout'}
        except Exception as e:
            fetch_quotes_status_queue.put(f"Error: {getattr(quote, 'company_name', str(quote))}: {e}")
            return {'stock': getattr(quote, 'company_name', str(quote)), 'status': f'error: {e}'}

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(retrieve_and_store, quote) for quote in stock_list]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        fetch_quotes_status_queue.put("Stock quotes fetched and stored to DB")
        return jsonify({'message': 'Stock quotes fetched and stored to DB', 'results': results}), 200
    except Exception as e:
        logging.error(f"Error fetching stock quotes: {str(e)}", exc_info=True)
        fetch_quotes_status_queue.put("Error fetching stock quotes")
        return jsonify({'error': 'Error fetching stock quotes'}), 500


@stock_bp.route('/fetch_status')
def fetch_quotes_status():
    """Server-sent events stream for fetch quotes status"""
    def event_stream():
        while True:
            msg = fetch_quotes_status_queue.get()
            yield f"data: {msg}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")


@stock_bp.route('/list', methods=['GET'])
def list_stocks():
    """List all stocks with pagination and sorting"""
    from flask import request
    from app.utils.util import get_db_connection

    # Get pagination and sorting parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    sort_by = request.args.get('sort_by', 'company_name', type=str)
    sort_order = request.args.get('sort_order', 'asc', type=str)

    # Validate parameters
    per_page = min(max(per_page, 10), 100)  # Between 10 and 100
    page = max(page, 1)

    # Allowed sort columns
    allowed_sort_columns = [
        'company_name', 'security_id', 'current_value', 'change', 'p_change',
        'day_high', 'day_low', 'previous_close', 'industry', 'updated_on'
    ]

    if sort_by not in allowed_sort_columns:
        sort_by = 'company_name'

    if sort_order.lower() not in ['asc', 'desc']:
        sort_order = 'asc'

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get total count
        cursor.execute('SELECT COUNT(*) FROM stock_quotes')
        total_count = cursor.fetchone()[0]

        # Calculate offset
        offset = (page - 1) * per_page

        # Build query with sorting
        query = f'''
            SELECT
                id, company_name, security_id, scrip_code, current_value,
                change, p_change, day_high, day_low, previous_close,
                previous_open, high_52week, low_52week, industry,
                market_cap_full, total_traded_value, updated_on, stock_status
            FROM stock_quotes
            ORDER BY {sort_by} {sort_order.upper()}
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
                'high_52week': row[11],
                'low_52week': row[12],
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
        logging.error(f"Error listing stocks: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error fetching stocks'}), 500
