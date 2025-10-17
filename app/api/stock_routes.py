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
        err_msg = f"Error fetching stock quotes: {str(e)}"
        logging.error(err_msg, exc_info=True)
        fetch_quotes_status_queue.put(err_msg)
        return jsonify({'error': err_msg}), 500


@stock_bp.route('/fetch_status')
def fetch_quotes_status():
    """Server-sent events stream for fetch quotes status"""
    def event_stream():
        while True:
            msg = fetch_quotes_status_queue.get()
            yield f"data: {msg}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")
