"""
Prediction API routes for stock prediction operations
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
from app.utils.websocket_manager import websocket_manager
from app.db.services.prediction_service import PredictionService
from app.api.watchlist_routes import get_user_watchlist_stocks

prediction_bp = Blueprint('prediction', __name__, url_prefix='/api/predictions')

# Queue for prediction status updates
status_queue = queue.Queue()


@prediction_bp.route('/', methods=['GET'])
def get_predictions():
    """Get top stock predictions with pagination"""
    logging.info("Fetching top stock predictions")
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 2000))
    
    result = PredictionService.get_top_predictions(page, page_size)
    logging.info(f"Found {len(result['predictions'])} predictions (page {page})")
    
    return jsonify(result), 200


@prediction_bp.route('/trigger', methods=['POST'])
def trigger_prediction():
    """Trigger batch prediction process for all stocks"""
    logging.info("Starting batch prediction process")
    status_queue.put("Starting batch prediction process...")
    websocket_manager.emit_prediction_progress({
        'status': 'started',
        'message': 'Starting batch prediction process...',
        'timestamp': datetime.now().isoformat()
    })
    
    offset = 0
    batch_size = 3

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        while True:
            batch = fetch_quotes_batch(batch_size, offset)
            if len(batch) == 0:
                msg = f"No more batches to process, finished at {datetime.now()}"
                logging.info(msg)
                status_queue.put(msg)
                websocket_manager.emit_prediction_progress({
                    'status': 'completed',
                    'message': msg,
                    'timestamp': datetime.now().isoformat()
                })
                break
            else:
                for quote in batch:
                    msg = f"Processing prediction for: {getattr(quote, 'company_name', str(quote))}"
                    logging.info(f"{msg} [Thread: {threading.current_thread().name}]")
                    status_queue.put(msg)
                    websocket_manager.emit_prediction_progress({
                        'status': 'processing',
                        'company_name': getattr(quote, 'company_name', str(quote)),
                        'message': msg,
                        'timestamp': datetime.now().isoformat()
                    })
                    futures.append(executor.submit(prediction_executor, quote.__dict__))
                    status_queue.put(f"Running prediction_executor for: {getattr(quote, 'company_name', str(quote))}")

            for future in as_completed(futures):
                try:
                    _ = future.result()  # Result not used, just ensuring completion
                    status_queue.put(msg)
                except Exception as e:
                    err_msg = f"Error during prediction: {str(e)}"
                    logging.error(err_msg, exc_info=True)
                    status_queue.put(err_msg)
                    websocket_manager.emit_prediction_progress({
                        'status': 'error',
                        'message': err_msg,
                        'timestamp': datetime.now().isoformat()
                    })

            offset += batch_size

    status_queue.put("Predictions triggered and data stored to DB")
    websocket_manager.emit_prediction_progress({
        'status': 'completed',
        'message': 'All predictions completed and stored to DB',
        'timestamp': datetime.now().isoformat()
    })
    return jsonify({'message': 'Predictions triggered and data stored to DB'}), 200


@prediction_bp.route('/trigger_watchlist', methods=['POST'])
@login_required
def trigger_watchlist_prediction():
    """Trigger predictions for user's watchlist stocks"""
    logging.info("Starting prediction for watchlist stocks")
    status_queue.put("Starting prediction for watchlist stocks...")
    
    try:
        watchlist_stocks = get_user_watchlist_stocks(current_user.id)
    except Exception as e:
        logging.error(f"Error fetching watchlist: {str(e)}", exc_info=True)
        status_queue.put("Error fetching watchlist")
        return jsonify({'message': 'Error fetching watchlist'}), 500

    if not watchlist_stocks:
        msg = "No stocks in watchlist"
        status_queue.put(msg)
        return jsonify({'message': msg}), 404

    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Create a mapping of futures to quotes
        future_to_quote = {}
        for quote in watchlist_stocks:
            msg = f"Processing prediction for: {getattr(quote, 'company_name', str(quote))}"
            logging.info(msg)
            status_queue.put(msg)
            future = executor.submit(prediction_executor, quote.__dict__)
            future_to_quote[future] = quote

        for future in as_completed(future_to_quote):
            quote = future_to_quote[future]
            company_name = getattr(quote, 'company_name', 'Unknown')
            try:
                _ = future.result()  # Result not used, just ensuring completion
                results.append({'stock': company_name, 'status': 'done'})
                status_queue.put(f"Prediction complete for {company_name}")
            except Exception as e:
                logging.error(f"Error during prediction: {str(e)}", exc_info=True)
                results.append({'stock': company_name, 'status': 'error'})
                status_queue.put(f"Error during prediction for {company_name}")

    status_queue.put("Watchlist predictions triggered and data stored to DB")
    return jsonify({'message': 'Watchlist predictions triggered and data stored to DB', 'results': results}), 200


@prediction_bp.route('/status')
def prediction_status():
    """Server-sent events stream for prediction status"""
    def event_stream():
        while True:
            msg = status_queue.get()
            yield f"data: {msg}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")
