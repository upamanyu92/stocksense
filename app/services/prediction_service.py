# Prediction service entry point
import logging
import schedule
from bsedata.bse import BSE
from datetime import datetime
from flask import Flask, jsonify

from app.db.db_executor import execute_query
from app.models.keras_model import predict_max_profit
from app.models.training_script import download_stock_data
from app.utils.util import predict_algo
from app.agents.prediction_coordinator import PredictionCoordinator

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Initialize the agentic prediction coordinator
prediction_coordinator = PredictionCoordinator(min_confidence=0.6)


def prediction_executor(data):
    """Execute prediction for a given stock."""
    try:
        stock_symbol = data.get('security_id')
        if not stock_symbol:
            logger.warning("No security_id provided in data")
            return
            
        stock_symbol_yahoo = stock_symbol + '.BO'
        logger.info(f"Starting prediction for {stock_symbol_yahoo}")
        
        # Use agentic prediction system for improved accuracy
        try:
            result = prediction_coordinator.predict(stock_symbol_yahoo, validate=True)
            predicted_price = result['prediction']
            confidence = result['confidence']
            decision = result['decision']
            
            logger.info(f"{stock_symbol_yahoo}: Predicted={predicted_price:.2f}, Confidence={confidence:.2f}, Decision={decision}")
            
            # Only use prediction if decision is 'accept' or 'caution'
            if decision == 'reject':
                logger.warning(f"{stock_symbol_yahoo}: Low confidence, using fallback method")
                predicted_price = predict_max_profit(stock_symbol_yahoo)
        except Exception as e:
            logger.error(f"{stock_symbol_yahoo}: Agentic prediction failed, using fallback - {str(e)}")
            predicted_price = predict_max_profit(stock_symbol_yahoo)

        # Handle both string and float values for current_value
        current_value = data['current_value']
        current_price = float(current_value.replace(',', '') if isinstance(current_value, str) else current_value)
        
        # Check and create row if not exists
        query = 'SELECT * FROM predictions WHERE security_id = ?'
        row = execute_query(query, (stock_symbol,), fetchone=True)
        
        if row:
            execute_query('''
                UPDATE predictions
                SET company_name = ?, current_price = ?, predicted_price = ?, prediction_date = ?
                WHERE security_id = ?
            ''', (data.get('company_name'), current_price, predicted_price,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'), stock_symbol), commit=True)
        else:
            execute_query('''
                INSERT INTO predictions (company_name, security_id, current_price, predicted_price, prediction_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (data.get('company_name'), stock_symbol, current_price, predicted_price,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')), commit=True)
                  
        logger.info(f"{stock_symbol_yahoo}: Prediction saved successfully")
    except Exception as e:
        logger.error(f"Failed to update predictions: {str(e)}", exc_info=True)


def update_database():
    """Update database with stock predictions using scheduler."""
    logger.info("Scheduler started")
    b = BSE()
    b.updateScripCodes()
    funds = b.getScripCodes()
    stock_symbol = None

    for code, name in funds.items():
        try:
            quote = b.getQuote(code)
            stock_symbol = quote.get('securityID')
            stock_symbol_yahoo = stock_symbol + '.BO'
            
            query = 'SELECT active FROM predictions_linear WHERE security_id = ?'
            row = execute_query(query, (stock_symbol,), fetchone=True)
            
            if row is None or row['active'] == 1:
                stock_data = download_stock_data(stock_symbol_yahoo)
                predicted_price = predict_algo(stock_data, stock_symbol)
                current_price = float(quote['currentValue'].replace(',', ''))
                
                logger.info(f"{quote.get('companyName')}: Current={current_price:.2f}, Predicted={predicted_price:.2f}")
                
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
                execute_query(query, (quote.get('companyName'), stock_symbol, current_price, predicted_price,
                              datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 1), commit=True)
            else:
                logger.debug(f"{quote.get('companyName')}: Skipped (inactive)")

        except Exception as e:
            logger.error(f"{stock_symbol}: Prediction error - {str(e)}")
            if str(e) == "Inactive stock":
                query = 'UPDATE predictions_linear SET active = 0 WHERE security_id = ?'
                execute_query(query, (stock_symbol,), commit=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Start the scheduler
    schedule.every(1).minutes.do(update_database)

    # Flask route for monitoring
    @app.route('/')
    def index():
        return jsonify({"message": "Scheduler and Updater Service Running"}), 200

    app.run(host='0.0.0.0', port=5001, debug=True)
