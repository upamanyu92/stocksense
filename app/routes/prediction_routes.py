"""
Prediction-related API routes.
"""
import logging
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from flask import Blueprint, jsonify, request, Response
from flask_login import login_required, current_user

from app.db.db_executor import fetch_quotes_batch
from app.services.prediction_service import prediction_executor
from app.routes.watchlist_routes import get_user_watchlist_stocks
from app.utils.util import get_db_connection

prediction_bp = Blueprint('prediction', __name__)

logger = logging.getLogger(__name__)

# Status queues for predictions
status_queue = queue.Queue()
fetch_quotes_status_queue = queue.Queue()


@prediction_bp.route('/prediction_status')
def prediction_status():
    """Stream prediction status updates."""
    def event_stream():
        while True:
            msg = status_queue.get()
            yield f"data: {msg}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")


@prediction_bp.route('/fetch_quotes_status')
def fetch_quotes_status():
    """Stream stock quotes fetching status updates."""
    def event_stream():
        while True:
            msg = fetch_quotes_status_queue.get()
            yield f"data: {msg}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")


@prediction_bp.route('/fetch_stock_quotes', methods=['POST'])
def fetch_stock_quotes():
    """Fetch and store stock quotes for all stocks."""
    logger.info("fetch_stock_quotes endpoint triggered")
    fetch_quotes_status_queue.put("Starting stock quotes fetching process...")
    
    from app.db.db_executor import fetch_quotes, data_retriever_executor
    import concurrent.futures
    
    stock_list = fetch_quotes("")
    results = []
    
    def retrieve_and_store(quote):
        try:
            stock_name = getattr(quote, 'company_name', str(quote))
            fetch_quotes_status_queue.put(f"Processing stock: {stock_name}")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as single_executor:
                future = single_executor.submit(data_retriever_executor, fetch_quotes_status_queue, 1)
                result = future.result(timeout=30)
            
            fetch_quotes_status_queue.put(f"Done: {stock_name}")
            return {'stock': stock_name, 'status': 'done'}
        except concurrent.futures.TimeoutError:
            fetch_quotes_status_queue.put(f"Timeout: {stock_name}")
            return {'stock': stock_name, 'status': 'timeout'}
        except Exception as e:
            fetch_quotes_status_queue.put(f"Error: {stock_name}: {e}")
            return {'stock': stock_name, 'status': f'error: {e}'}

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(retrieve_and_store, quote) for quote in stock_list]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        fetch_quotes_status_queue.put("Stock quotes fetched and stored to DB")
        return jsonify({'message': 'Stock quotes fetched and stored to DB', 'results': results}), 200
    except Exception as e:
        err_msg = f"Error fetching stock quotes: {str(e)}"
        logger.error(err_msg, exc_info=True)
        fetch_quotes_status_queue.put(err_msg)
        return jsonify({'error': err_msg}), 500


@prediction_bp.route('/trigger_prediction', methods=['POST'])
def trigger_prediction():
    """Trigger batch prediction for all stocks."""
    logger.info("Starting batch prediction process")
    status_queue.put("Starting batch prediction process...")
    offset = 0
    batch_size = 3

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        while True:
            batch = fetch_quotes_batch(batch_size, offset)
            if len(batch) == 0:
                msg = f"Batch prediction completed at {datetime.now()}"
                logger.info(msg)
                status_queue.put(msg)
                break
            
            for quote in batch:
                company_name = getattr(quote, 'company_name', str(quote))
                msg = f"Processing prediction for: {company_name}"
                logger.info(msg)
                status_queue.put(msg)
                futures.append(executor.submit(prediction_executor, quote.__dict__))

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    err_msg = f"Error during prediction: {str(e)}"
                    logger.error(err_msg, exc_info=True)
                    status_queue.put(err_msg)

            offset += batch_size

    status_queue.put("Predictions triggered and data stored to DB")
    return jsonify({'message': 'Predictions triggered and data stored to DB'}), 200


@prediction_bp.route('/get_predictions', methods=['GET'])
def get_predictions():
    """Get top stock predictions with pagination."""
    logger.info("Fetching stock predictions")
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 2000))
    offset = (page - 1) * page_size
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM predictions')
    total = c.fetchone()[0]
    
    c.execute('''
        SELECT company_name, security_id, current_price, predicted_price, 
               (predicted_price - current_price) AS profit,
               prediction_date
        FROM predictions
        ORDER BY (predicted_price - current_price) / current_price DESC
        LIMIT ? OFFSET ?
    ''', (page_size, offset))
    rows = c.fetchall()
    conn.close()

    stocks = []
    for row in rows:
        stock = dict(row)
        stock['profit_percentage'] = ((stock['predicted_price'] - stock['current_price']) / stock['current_price']) * 100
        stocks.append(stock)

    logger.info(f"Retrieved {len(stocks)} predictions (page {page} of {(total + page_size - 1) // page_size})")
    return jsonify({
        'predictions': stocks,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size
    }), 200


@prediction_bp.route('/trigger_watchlist_prediction', methods=['POST'])
@login_required
def trigger_watchlist_prediction():
    """Trigger prediction for user's watchlist stocks."""
    logger.info(f"Starting watchlist prediction for user {current_user.id}")
    status_queue.put("Starting prediction for watchlist stocks...")
    
    try:
        watchlist_stocks = get_user_watchlist_stocks(current_user.id)
    except Exception as e:
        msg = f"Error fetching watchlist: {e}"
        logger.error(msg, exc_info=True)
        status_queue.put(msg)
        return jsonify({'message': msg}), 500

    if not watchlist_stocks:
        msg = "No stocks in watchlist"
        status_queue.put(msg)
        return jsonify({'message': msg}), 404

    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for quote in watchlist_stocks:
            company_name = getattr(quote, 'company_name', str(quote))
            logger.info(f"Queuing prediction for: {company_name}")
            status_queue.put(f"Processing prediction for: {company_name}")
            futures.append(executor.submit(prediction_executor, quote.__dict__))

        for future in as_completed(futures):
            try:
                future.result()
                results.append({'status': 'done'})
                status_queue.put("Prediction complete")
            except Exception as e:
                err_msg = f"Error during prediction: {str(e)}"
                logger.error(err_msg, exc_info=True)
                results.append({'status': f'error: {err_msg}'})
                status_queue.put(err_msg)

    status_queue.put("Watchlist predictions completed")
    return jsonify({'message': 'Watchlist predictions triggered and data stored to DB', 'results': results}), 200
