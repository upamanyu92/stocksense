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

from app.api.auth_routes import auth_bp
from app.api.watchlist_routes import watchlist_bp
from app.db.db_executor import fetch_quotes_batch, fetch_quotes
from app.services.auth_service import User
from app.services.background_worker import background_worker
from app.services.prediction_service import prediction_executor
from app.utils.disk_monitor import DiskSpaceMonitor
from app.utils.util import get_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

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
                break
            else:
                for quote in batch:
                    msg = f"Processing prediction for: {getattr(quote, 'company_name', str(quote))}"
                    logging.info(f"{msg} [Thread: {threading.current_thread().name}]")
                    status_queue.put(msg)
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

            offset += batch_size

    status_queue.put("Predictions triggered and data stored to DB")
    return jsonify({'message': 'Predictions triggered and data stored to DB'}), 200

@app.route('/get_predictions', methods=['GET'])
def get_top_stocks():
    logging.info("Fetching top stock predictions")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT company_name, security_id, current_price, predicted_price, 
               (predicted_price - current_price) AS profit,
               prediction_date
        FROM predictions
        ORDER BY (predicted_price - current_price) / current_price DESC
    ''')
    rows = c.fetchall()
    conn.close()

    stocks = []
    for row in rows:
        stock = dict(row)
        stock['profit_percentage'] = ((stock['predicted_price'] - stock['current_price']) / stock['current_price']) * 100
        stocks.append(stock)

    logging.info(f"Found {len(stocks)} predictions")
    return jsonify(stocks), 200

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

if __name__ == '__main__':
    port = int(os.environ.get('FLASK_PORT', 5005))
    logging.info(f"Starting StockSense application on port {port}")
    app.run(host='0.0.0.0', debug=False, port=port)
