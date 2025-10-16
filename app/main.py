# Main Flask application entry point
import json
import logging
import os
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from flask import Flask, jsonify, render_template, request, Response, redirect, url_for
from flask_cors import CORS
from flask_login import LoginManager, login_required, current_user
from flask_socketio import SocketIO, emit

from app.api.auth_routes import auth_bp
from app.api.watchlist_routes import watchlist_bp, get_user_watchlist_stocks
from app.db.db_executor import fetch_quotes_batch, fetch_quotes
from app.services.auth_service import User
from app.services.background_worker import background_worker
from app.services.prediction_service import prediction_executor
from app.services.price_streamer import price_streamer
from app.utils.disk_monitor import DiskSpaceMonitor
from app.utils.util import get_db_connection
from app.utils.websocket_manager import websocket_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Track application start time for uptime calculation
app_start_time = datetime.now()

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize WebSocket manager
websocket_manager.init_socketio(socketio)

# Set websocket manager in background worker
from app.services import background_worker as bg_worker_module
bg_worker_module.set_websocket_manager(websocket_manager)

# Set websocket manager in price streamer
price_streamer.set_websocket_manager(websocket_manager)

# Set websocket manager in prediction service
from app.services import prediction_service as pred_service_module
pred_service_module.set_websocket_manager(websocket_manager)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(watchlist_bp)

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))

status_queue = queue.Queue()  # For predictions
fetch_quotes_status_queue = queue.Queue()  # For fetch_stock_quotes

# Start background worker when app starts
@app.before_request
def start_background_worker():
    """Start the background worker before every request"""
    background_worker.start()
    # logging.info("Background worker started automatically")

@app.route('/search_quote/<company_name>', methods=['GET'])
def search_quote(company_name):
    logging.info(f"Searching for quote: {company_name}")
    data = fetch_quotes(company_name)
    logging.info(data)
    if not data or "quotes" not in data or len(data["quotes"]) == 0:
        return jsonify({"quotes": [], "message": "No data found"}), 404
    else:
        logging.info(f"Found {len(data['quotes'])} quotes")
        return jsonify(data["quotes"])

# @app.route('/predict', methods=['POST'])
# def predict():
#     data = request.get_json()
#     logging.info(f"Prediction request for: {data}")
#     prediction_executor(data)
#     return jsonify({'message': 'Prediction triggered'}), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker and monitoring"""
    return jsonify({"status": "healthy", "service": "stocksense"}), 200

@app.route('/prediction_status')
def prediction_status():
    def event_stream():
        while True:
            msg = status_queue.get()
            yield f"data: {msg}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/fetch_quotes_status')
def fetch_quotes_status():
    def event_stream():
        while True:
            msg = fetch_quotes_status_queue.get()
            yield f"data: {msg}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")


@app.route('/fetch_stock_quotes', methods=['POST'])
def fetch_stock_quotes():
    logging.info("Starting stock quotes fetching process")
    fetch_quotes_status_queue.put("Starting stock quotes fetching process...")
    logging.info("fetch_stock_quotes endpoint triggered")
    fetch_quotes_status_queue.put("fetch_stock_quotes endpoint triggered")
    from app.db.db_executor import fetch_quotes, data_retriever_executor
    stock_list = fetch_quotes("")  # Fetch all stocks, adjust as needed
    results = []
    def retrieve_and_store(quote):
        try:
            fetch_quotes_status_queue.put(f"Processing stock: {getattr(quote, 'company_name', str(quote))}")
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as single_executor:
                future = single_executor.submit(data_retriever_executor, fetch_quotes_status_queue, 1)
                result = future.result(timeout=30)
            fetch_quotes_status_queue.put(f"Done: {getattr(quote, 'company_name', str(quote))}")
            return {'stock': getattr(quote, 'company_name', str(quote)), 'status': 'done'}
        except concurrent.futures.TimeoutError:
            fetch_quotes_status_queue.put(f"Timeout: {getattr(quote, 'company_name', str(quote))}")
            return {'stock': getattr(quote, 'company_name', str(quote)), 'status': 'timeout'}
        except Exception as e:
            fetch_quotes_status_queue.put(f"Error: {getattr(quote, 'company_name', str(quote))}: {e}")
            return {'stock': getattr(quote, 'company_name', str(quote)), 'status': f'error: {e}'}

    try:
        import concurrent.futures
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


@app.route('/trigger_prediction', methods=['POST'])
def trigger_prediction():
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
                    result = future.result()
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

@app.route('/get_predictions', methods=['GET'])
def get_top_stocks():
    logging.info("Fetching top stock predictions")
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 2000))
    offset = (page - 1) * page_size
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT COUNT(*) FROM predictions
    ''')
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

    logging.info(f"Found {len(stocks)} predictions (page {page})")
    return jsonify({
        'predictions': stocks,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size
    }), 200

@app.route('/')
def index():
    """Redirect to login page"""
    if current_user.is_authenticated:
        return redirect(url_for('user_dashboard'))
    return redirect(url_for('auth.login'))

@app.route('/dashboard')
@login_required
def user_dashboard():
    """User dashboard page"""
    return render_template('dashboard.html', username=current_user.username)

@app.route('/api/system/status')
@login_required
def system_status():
    """Get system status including background worker and disk space"""
    worker_status = background_worker.get_status()
    disk_usage = DiskSpaceMonitor.get_disk_usage()
    model_stats = DiskSpaceMonitor.get_model_directory_size()
    
    return jsonify({
        'background_worker': worker_status,
        'disk_usage': disk_usage,
        'model_stats': model_stats
    }), 200

@app.route('/api/system/uptime')
@login_required
def get_uptime():
    """Get application uptime"""
    uptime_seconds = (datetime.now() - app_start_time).total_seconds()
    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    
    uptime_str = ""
    if days > 0:
        uptime_str += f"{days}d "
    if hours > 0 or days > 0:
        uptime_str += f"{hours}h "
    uptime_str += f"{minutes}m"
    
    return jsonify({
        'uptime': uptime_str,
        'uptime_seconds': int(uptime_seconds)
    }), 200

@app.route('/api/system/cleanup_models', methods=['POST'])
@login_required
def cleanup_models():
    """Cleanup old models"""
    try:
        keep_newest = request.json.get('keep_newest', 2) if request.json else 2
        result = DiskSpaceMonitor.cleanup_old_models(keep_newest)
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/background_worker/status')
@login_required
def background_worker_status():
    """Get background worker status stream"""
    def event_stream():
        while True:
            status = background_worker.get_status()
            yield f"data: {json.dumps(status)}\n\n"
            import time
            time.sleep(2)
    return Response(event_stream(), mimetype="text/event-stream")


@app.route('/api/background-status', methods=['GET'])
def background_status():
    """Return real-time status of background worker"""
    return jsonify(background_worker.get_status())

@app.route('/api/price_stream/start', methods=['POST'])
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

@app.route('/api/price_stream/stop', methods=['POST'])
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

@app.route('/api/price_stream/status', methods=['GET'])
@login_required
def price_streaming_status():
    """Get price streaming status"""
    return jsonify({
        'streaming': price_streamer.streaming,
        'watched_symbols': price_streamer.get_watched_symbols(),
        'update_interval': price_streamer.update_interval
    }), 200

@app.route('/api/price/<symbol>', methods=['GET'])
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

# WebSocket event handlers for real-time updates
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logging.info(f"Client connected: {request.sid}")
    emit('connection_status', {'status': 'connected', 'message': 'Connected to StockSense'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logging.info(f"Client disconnected: {request.sid}")

@socketio.on('subscribe_predictions')
def handle_subscribe_predictions():
    """Subscribe to real-time prediction updates"""
    logging.info(f"Client {request.sid} subscribed to prediction updates")
    emit('subscription_confirmed', {'type': 'predictions'})

@socketio.on('subscribe_watchlist')
def handle_subscribe_watchlist(data=None):
    """Subscribe to real-time watchlist updates"""
    user_id = data.get('user_id') if data else None
    logging.info(f"Client {request.sid} subscribed to watchlist updates for user {user_id}")
    emit('subscription_confirmed', {'type': 'watchlist'})

@socketio.on('subscribe_stock_prices')
def handle_subscribe_stock_prices(data):
    """Subscribe to real-time stock price updates"""
    symbols = data.get('symbols', []) if data else []
    logging.info(f"Client {request.sid} subscribed to price updates for {len(symbols)} stocks")
    
    # Add symbols to price streamer
    for symbol in symbols:
        price_streamer.add_symbol(symbol)
    
    # Start streaming if not already running
    if not price_streamer.streaming:
        price_streamer.start_streaming()
    
    emit('subscription_confirmed', {'type': 'stock_prices', 'symbols': symbols})

@socketio.on('unsubscribe_stock_prices')
def handle_unsubscribe_stock_prices(data):
    """Unsubscribe from stock price updates"""
    symbols = data.get('symbols', []) if data else []
    logging.info(f"Client {request.sid} unsubscribed from price updates for {len(symbols)} stocks")
    
    # Remove symbols from price streamer
    for symbol in symbols:
        price_streamer.remove_symbol(symbol)
    
    emit('unsubscription_confirmed', {'type': 'stock_prices', 'symbols': symbols})

@socketio.on('request_system_status')
def handle_system_status_request():
    """Send current system status via WebSocket"""
    worker_status = background_worker.get_status()
    disk_usage = DiskSpaceMonitor.get_disk_usage()
    model_stats = DiskSpaceMonitor.get_model_directory_size()
    
    emit('system_status', {
        'background_worker': worker_status,
        'disk_usage': disk_usage,
        'model_stats': model_stats
    })

def emit_prediction_update(prediction_data):
    """Emit real-time prediction update to all connected clients"""
    socketio.emit('prediction_update', prediction_data, broadcast=True)

def emit_watchlist_update(watchlist_data):
    """Emit real-time watchlist update to all connected clients"""
    socketio.emit('watchlist_update', watchlist_data, broadcast=True)

def emit_stock_price_update(price_data):
    """Emit real-time stock price update to all connected clients"""
    socketio.emit('stock_price_update', price_data, broadcast=True)

def emit_background_worker_status(status_data):
    """Emit background worker status update to all connected clients"""
    socketio.emit('background_worker_status', status_data, broadcast=True)

@app.route('/trigger_watchlist_prediction', methods=['POST'])
@login_required
def trigger_watchlist_prediction():
    logging.info("Starting prediction for watchlist stocks")
    status_queue.put("Starting prediction for watchlist stocks...")
    # Fetch user's watchlist stocks
    try:
        watchlist_stocks = get_user_watchlist_stocks(current_user.id)
    except Exception as e:
        msg = f"Error fetching watchlist: {e}"
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
            msg = f"Processing prediction for: {getattr(quote, 'company_name', str(quote))}"
            logging.info(msg)
            status_queue.put(msg)
            futures.append(executor.submit(prediction_executor, quote.__dict__))

        for future in as_completed(futures):
            try:
                result = future.result()
                results.append({'stock': getattr(result, 'company_name', str(result)), 'status': 'done'})
                status_queue.put("Prediction complete")
            except Exception as e:
                err_msg = f"Error during prediction: {str(e)}"
                logging.error(err_msg, exc_info=True)
                results.append({'stock': None, 'status': f'error: {err_msg}'})
                status_queue.put(err_msg)

    status_queue.put("Watchlist predictions triggered and data stored to DB")
    return jsonify({'message': 'Watchlist predictions triggered and data stored to DB', 'results': results}), 200

if __name__ == '__main__':
    port = int(os.environ.get('FLASK_PORT', 5005))
    logging.info(f"Starting StockSense application on port {port}")
    socketio.run(app, host='0.0.0.0', debug=False, port=port, allow_unsafe_werkzeug=True)
