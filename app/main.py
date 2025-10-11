# Main Flask application entry point
import threading

from flask import Flask, jsonify, render_template, request, Response
from flask_cors import CORS
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import os
import queue

from app.db.db_executor import fetch_quotes_batch, fetch_quotes, get_top_stocks as db_get_top_stocks, get_db_connection
from app.services.prediction_service import prediction_executor
from app.models.training_script import train_transformer_model, download_stock_data
from app.models.keras_model import predict_max_profit
from app.db.db_executor import fetch_quotes, upsert_prediction
from app.api.routes import api as api_blueprint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'stocksense_default_secret')
CORS(app)
app.register_blueprint(api_blueprint, url_prefix='/api')

status_queue = queue.Queue()  # For predictions
fetch_quotes_status_queue = queue.Queue()  # For fetch_stock_quotes

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

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        company_name = data.get('company_name')
        if not company_name:
            return jsonify({'error': 'Company name is required'}), 400

        # Get stock quote information
        quotes_data = fetch_quotes(company_name)
        if not quotes_data or not quotes_data.get('quotes'):
            return jsonify({'error': 'Company not found'}), 404

        quote = quotes_data['quotes'][0]  # Get the first matching quote
        stock_symbol = quote['security_id']
        stock_symbol_yahoo = f"{stock_symbol}.BO"

        status_queue.put(f"Starting prediction process for {company_name} ({stock_symbol})")

        # Check for existing model or train new one
        model_path = f"app/model/saved_models/{stock_symbol}_transformer_latest"
        try:
            predicted_price = predict_max_profit(stock_symbol_yahoo)
            status_queue.put(f"Using existing model for prediction")
        except (FileNotFoundError, Exception) as e:
            status_queue.put(f"No existing model found or error occurred. Training new model...")
            # Download data and train new model
            stock_data = download_stock_data(stock_symbol_yahoo)
            if stock_data is None or stock_data.empty:
                return jsonify({'error': 'Unable to download stock data'}), 500

            model, _, _ = train_transformer_model(stock_symbol)
            predicted_price = predict_max_profit(stock_symbol_yahoo)
            status_queue.put(f"New model trained successfully")

        # Store prediction
        current_price = float(quote['current_value'].replace(',', '') if isinstance(quote['current_value'], str)
                            else quote['current_value'])

        prediction_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        upsert_prediction(
            company_name=quote['company_name'],
            security_id=stock_symbol,
            current_price=current_price,
            predicted_price=predicted_price,
            prediction_date=prediction_date
        )

        # Calculate profit percentage
        profit_percentage = ((predicted_price - current_price) / current_price) * 100

        result = {
            'company_name': quote['company_name'],
            'security_id': stock_symbol,
            'current_price': current_price,
            'predicted_price': round(predicted_price, 2),
            'profit_percentage': round(profit_percentage, 2),
            'prediction_date': prediction_date,
            'quote_info': {
                'day_high': quote.get('day_high', '-'),
                'day_low': quote.get('day_low', '-'),
                'change': quote.get('change', '-'),
                'volume': quote.get('total_traded_quantity', '-'),
                'market_cap': quote.get('market_cap_full', '-')
            }
        }

        status_queue.put(f"Prediction complete for {company_name}")
        return jsonify(result), 200

    except Exception as e:
        error_msg = f"Error during prediction: {str(e)}"
        logging.error(error_msg, exc_info=True)
        status_queue.put(error_msg)
        return jsonify({'error': error_msg}), 500

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
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
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
    stocks = db_get_top_stocks()
    logging.info(f"Found {len(stocks)} predictions")
    return stocks

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/account')
def account_page():
    return render_template('account.html')

@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/')
def index():
    return render_template('dashboard.html')

if __name__ == '__main__':
    port = int(os.environ.get('FLASK_PORT', 5005))
    logging.info(f"Starting StockSense application on port {port}")
    app.run(host='0.0.0.0', debug=False, port=port)
