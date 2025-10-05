# Prediction service entry point
from flask import Flask, jsonify
import schedule
from bsedata.bse import BSE
from datetime import datetime
import logging

from app.db.db_executor import execute_query
from app.models.keras_model import predict_max_profit
from app.models.training_script import download_stock_data
from app.utils.util import predict_algo, check_index_existence

app = Flask(__name__)


def prediction_executor(data):
    try:
        stock_symbol = data.get('security_id')
        print(data)
        if stock_symbol:
            stock_symbol_yahoo = stock_symbol + '.BO'
            logging.info(f"prediction_executor: started for {stock_symbol_yahoo} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            predicted_price = predict_max_profit(stock_symbol_yahoo)

            # Handle both string and float values for current_value
            current_value = data['current_value']
            if isinstance(current_value, str):
                current_price = float(current_value.replace(',', ''))
            else:
                current_price = float(current_value)
            # check and create row if not exists
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
    except Exception as e:
        logging.error(f"Failed to update predictions: {str(e)}", exc_info=True)


def update_database():
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
                execute_query(query, (quote.get('companyName'), stock_symbol, current_price, predicted_price,
                                      datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 1), commit=True)
            else:
                logger.warning(f"Stock {stock_symbol} is marked as inactive for {quote.get('companyName')}")

        except Exception as e:
            logger.error(f"Error predicting for {stock_symbol}: {str(e)}")
            if str(e) == "Inactive stock":
                query = 'UPDATE predictions_linear SET active = 0 WHERE security_id = ?'
                execute_query(query, (stock_symbol,), commit=True)

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
