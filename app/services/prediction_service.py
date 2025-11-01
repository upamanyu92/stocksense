# Prediction service entry point
from flask import Flask, jsonify
import schedule
import yfinance as yf
from datetime import datetime
import logging

from app.db.db_executor import execute_query
from app.models.keras_model import predict_max_profit
from app.models.training_script import download_stock_data
from app.utils.util import predict_algo, check_index_existence
from app.agents.prediction_coordinator import PredictionCoordinator
from app.db.services.prediction_service import PredictionService
from app.db.data_models import Prediction
from app.utils.yfinance_utils import get_quote_with_retry

app = Flask(__name__)

# Initialize the agentic prediction coordinator
prediction_coordinator = PredictionCoordinator(min_confidence=0.6)

# WebSocket manager - will be set from main.py
websocket_manager = None

def set_websocket_manager(manager):
    """Set the websocket manager instance"""
    global websocket_manager
    websocket_manager = manager


def prediction_executor(data):
    try:
        stock_symbol = data.get('security_id')
        company_name = data.get('company_name')
        print(data)
        if stock_symbol:
            stock_symbol_yahoo = stock_symbol + '.BO'
            logging.info(f"prediction_executor: started for {stock_symbol_yahoo} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Emit prediction start event
            if websocket_manager:
                websocket_manager.emit_prediction_progress({
                    'status': 'processing',
                    'company_name': company_name,
                    'security_id': stock_symbol,
                    'message': f'Processing prediction for {company_name}',
                    'timestamp': datetime.now().isoformat()
                })
            
            # Use agentic prediction system for improved accuracy
            try:
                result = prediction_coordinator.predict(stock_symbol_yahoo, validate=True)
                predicted_price = result['prediction']
                confidence = result['confidence']
                decision = result['decision']
                
                # Log agentic prediction details
                logging.info(f"Agentic prediction: {predicted_price:.2f}, Confidence: {confidence:.2f}, Decision: {decision}")
                logging.info(f"Recommendation: {result['recommendation']}")
                
                # Only use prediction if decision is 'accept' or 'caution'
                if decision == 'reject':
                    logging.warning(f"Prediction rejected due to low confidence. Falling back to traditional method.")
                    predicted_price = predict_max_profit(stock_symbol_yahoo)
            except Exception as e:
                logging.error(f"Agentic prediction failed: {str(e)}. Falling back to traditional method.")
                predicted_price = predict_max_profit(stock_symbol_yahoo)
                confidence = 0.5
                decision = 'fallback'

            # Handle both string and float values for current_value
            current_value = data['current_value']
            if isinstance(current_value, str):
                current_price = float(current_value.replace(',', ''))
            else:
                current_price = float(current_value)
            
            # Create or update prediction using the service layer
            prediction = Prediction(
                company_name=data.get('company_name'),
                security_id=stock_symbol,
                current_price=current_price,
                predicted_price=predicted_price,
                prediction_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            PredictionService.create(prediction)
            
            # Emit prediction complete event with results
            if websocket_manager:
                profit_percentage = ((predicted_price - current_price) / current_price) * 100
                websocket_manager.emit_prediction_update({
                    'company_name': company_name,
                    'security_id': stock_symbol,
                    'current_price': current_price,
                    'predicted_price': predicted_price,
                    'profit_percentage': profit_percentage,
                    'confidence': confidence if 'confidence' in locals() else 0.5,
                    'decision': decision if 'decision' in locals() else 'fallback',
                    'prediction_date': datetime.now().isoformat(),
                    'timestamp': datetime.now().isoformat()
                })
                
    except Exception as e:
        logging.error(f"Failed to update predictions: {str(e)}", exc_info=True)
        # Emit error event
        if websocket_manager:
            websocket_manager.emit_prediction_progress({
                'status': 'error',
                'company_name': data.get('company_name'),
                'security_id': data.get('security_id'),
                'message': f'Error processing prediction: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })


def update_database():
    logger.info("Scheduler started")
    
    # Load stock list from existing stk.json
    import json
    import os
    
    stock_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'stk.json')
    try:
        with open(stock_file_path, 'r') as f:
            funds = json.load(f)
    except FileNotFoundError:
        logger.error("Stock list file not found")
        return
    
    stock_symbol = None

    for code, name in funds.items():
        try:
            # Get stock symbol from database
            query = 'SELECT stock_symbol FROM stock_quotes WHERE scrip_code = ? OR company_name = ?'
            row = execute_query(query, (code, name), fetchone=True)
            
            if not row or not row.get('stock_symbol'):
                logger.debug(f"Skipping {name} - no symbol mapping")
                continue
            
            stock_symbol = row['stock_symbol']
            stock_symbol_yahoo = stock_symbol if stock_symbol.endswith('.BO') or stock_symbol.endswith('.NS') else stock_symbol + '.BO'
            
            query = 'SELECT active FROM predictions_linear WHERE security_id = ?'
            row = execute_query(query, (stock_symbol.replace('.BO', '').replace('.NS', ''),), fetchone=True)
            if row is None or row['active'] == 1:
                stock_data = download_stock_data(stock_symbol_yahoo)
                predicted_price = predict_algo(stock_data, stock_symbol)
                
                # Get current price from yfinance
                quote = get_quote_with_retry(stock_symbol_yahoo)
                if not quote:
                    logger.warning(f"Failed to get quote for {stock_symbol_yahoo}, skipping")
                    continue
                
                current_price = float(quote['currentValue']) if isinstance(quote['currentValue'], (int, float)) else float(str(quote['currentValue']).replace(',', ''))
                
                logger.info(f"Predicted price: {predicted_price}, Current price: {current_price} for {quote.get('companyName')}")
                query = '''
                    INSERT INTO predictions_linear (company_name, security_id, current_price, predicted_price, prediction_date, active)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(security_id) DO UPDATE SET
                        company_name=excluded.company_name,
                        current_price=excluded.current_price,
                        predicted_price=excluded.predicted_price,
                        prediction_date=excluded.prediction_date,
                        active=excluded.active
                '''
                execute_query(query, (quote.get('companyName'), stock_symbol.replace('.BO', '').replace('.NS', ''), current_price, predicted_price,
                                      datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 1), commit=True)
            else:
                logger.warning(f"Stock {stock_symbol} is marked as inactive for {name}")

        except Exception as e:
            logger.error(f"Error predicting for {stock_symbol}: {str(e)}")
            if str(e) == "Inactive stock":
                query = 'UPDATE predictions_linear SET active = 0 WHERE security_id = ?'
                execute_query(query, (stock_symbol.replace('.BO', '').replace('.NS', '') if stock_symbol else code,), commit=True)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    # Start the scheduler
    schedule.every(1).minutes.do(update_database)

    # Flask route for monitoring
    @app.route('/')
    def index():
        return jsonify({"message": "Scheduler and Updater Service Running"}), 200

    app.run(host='0.0.0.0', port=5001, debug=True)
