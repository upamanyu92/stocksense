"""
Prediction API routes for stock prediction operations
"""
import logging
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime

from flask import Blueprint, jsonify, request, Response
from flask_login import login_required, current_user

from app.db.session_manager import get_session_manager
from app.db.services.stock_quote_service import StockQuoteService
from app.db.data_models import StockQuote
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
            batch = StockQuoteService.get_batch(batch_size, offset)
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
                    company_name = getattr(quote, 'company_name', 'Unknown')
                    msg = f"Processing prediction for: {company_name}"
                    logging.info(f"{msg} [Thread: {threading.current_thread().name}]")
                    status_queue.put(msg)
                    websocket_manager.emit_prediction_progress({
                        'status': 'processing',
                        'company_name': company_name,
                        'message': msg,
                        'timestamp': datetime.now().isoformat()
                    })
                    # quote is a StockQuote dataclass, convert to dict
                    from dataclasses import asdict
                    futures.append(executor.submit(prediction_executor, asdict(quote)))
                    status_queue.put(f"Running prediction_executor for: {company_name}")

            for future in as_completed(futures):
                try:
                    _ = future.result()  # Result not used, just ensuring completion
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
        for quote_dict in watchlist_stocks:
            company_name = quote_dict.get('company_name', 'Unknown')
            msg = f"Processing prediction for: {company_name}"
            logging.info(msg)
            status_queue.put(msg)
            
            # WatchlistService.get_watchlist returns dicts that might not have all fields 
            # needed by prediction_executor. We need to fetch the full quote.
            full_quote = StockQuoteService.get_by_company_name(company_name)
            if not full_quote:
                # Try by symbol
                symbol = quote_dict.get('stock_symbol')
                db = get_session_manager()
                row = db.fetch_one('SELECT * FROM stock_quotes WHERE security_id = ? OR stock_symbol = ?', (symbol, symbol))
                if row:
                    full_quote = StockQuote(**row)
            
            if full_quote:
                future = executor.submit(prediction_executor, asdict(full_quote))
                future_to_quote[future] = company_name
            else:
                logging.warning(f"Could not find full quote for {company_name}")
                results.append({'stock': company_name, 'status': 'skipped (no quote)'})

        for future in as_completed(future_to_quote):
            company_name = future_to_quote[future]
            try:
                _ = future.result()  # Result not used, just ensuring completion
                results.append({'stock': company_name, 'status': 'done'})
                status_queue.put(f"Prediction complete for {company_name}")
            except Exception as e:
                logging.error(f"Error during prediction for {company_name}: {str(e)}", exc_info=True)
                results.append({'stock': company_name, 'status': 'error'})
                status_queue.put(f"Error during prediction for {company_name}")

    status_queue.put("Watchlist predictions triggered and data stored to DB")
    return jsonify({'message': 'Watchlist predictions triggered and data stored to DB', 'results': results}), 200


@prediction_bp.route('/stock/<security_id>', methods=['GET'])
def get_stock_prediction(security_id):
    """Get prediction for a specific stock"""
    try:
        result = PredictionService.get_prediction_by_security_id(security_id)
        if result:
            return jsonify({'success': True, 'prediction': result}), 200
        else:
            return jsonify({'success': False, 'message': 'No prediction found'}), 404
    except Exception as e:
        logging.error(f"Error fetching prediction: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@prediction_bp.route('/trigger_single', methods=['POST'])
@login_required
def trigger_single_prediction():
    """Trigger prediction for a single stock by symbol or company name"""
    data = request.get_json()
    stock_symbol = data.get('stock_symbol')
    company_name = data.get('company_name')
    
    if not stock_symbol and not company_name:
        return jsonify({'success': False, 'error': 'Stock symbol or company name required'}), 400
    
    logging.info(f"Starting single stock prediction for: {stock_symbol or company_name}")
    
    try:
        # Find the stock in the database
        db = get_session_manager()
        
        if stock_symbol:
            row = db.fetch_one('SELECT * FROM stock_quotes WHERE security_id = ? OR scrip_code = ? OR stock_symbol = ?', 
                         (stock_symbol, stock_symbol, stock_symbol))
        else:
            row = db.fetch_one('SELECT * FROM stock_quotes WHERE company_name = ?', (company_name,))
        
        if not row:
            return jsonify({'success': False, 'error': 'Stock not found'}), 404
        
        # Emit start status
        websocket_manager.emit_prediction_progress({
            'status': 'started',
            'company_name': row.get('company_name'),
            'security_id': row.get('security_id'),
            'message': f"Starting prediction for {row.get('company_name')}",
            'timestamp': datetime.now().isoformat()
        })
        
        # Run prediction in background thread
        def run_prediction(quote_dict):
            try:
                prediction_executor(quote_dict)
                websocket_manager.emit_prediction_progress({
                    'status': 'completed',
                    'company_name': quote_dict.get('company_name'),
                    'security_id': quote_dict.get('security_id'),
                    'message': f"Prediction completed for {quote_dict.get('company_name')}",
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logging.error(f"Error in prediction: {str(e)}", exc_info=True)
                websocket_manager.emit_prediction_progress({
                    'status': 'error',
                    'company_name': quote_dict.get('company_name'),
                    'security_id': quote_dict.get('security_id'),
                    'message': f"Error: {str(e)}",
                    'timestamp': datetime.now().isoformat()
                })
        
        thread = threading.Thread(target=run_prediction, args=(row,), daemon=True)
        thread.start()
        
        return jsonify({
            'success': True, 
            'message': f"Prediction started for {row.get('company_name')}",
            'company_name': row.get('company_name'),
            'security_id': row.get('security_id')
        }), 200
        
    except Exception as e:
        logging.error(f"Error triggering prediction: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@prediction_bp.route('/status')
def prediction_status():
    """Server-sent events stream for prediction status"""
    def event_stream():
        while True:
            msg = status_queue.get()
            yield f"data: {msg}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")
