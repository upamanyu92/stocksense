# Prediction service entry point
from flask import Flask, jsonify
import schedule
from bsedata.bse import BSE
from datetime import datetime
import logging

from app.db.db_executor import (
    get_prediction_by_security_id,
    upsert_prediction,
    get_linear_prediction_active_status,
    upsert_linear_prediction,
    set_linear_prediction_inactive
)
from app.models.keras_model import predict_max_profit
from app.models.training_script import download_stock_data
from app.utils.util import predict_algo

app = Flask(__name__)


def prediction_executor(data):
    try:
        stock_symbol = data.get('security_id')
        print(data)
        if stock_symbol:
            stock_symbol_yahoo = stock_symbol + '.BO'
            logging.info(f"prediction_executor: started for {stock_symbol_yahoo} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            predicted_price = predict_max_profit(stock_symbol_yahoo)

            current_value = data['current_value']
            if isinstance(current_value, str):
                current_price = float(current_value.replace(',', ''))
            else:
                current_price = float(current_value)
            upsert_prediction(
                data.get('company_name'),
                stock_symbol,
                current_price,
                predicted_price,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
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
            active_status = get_linear_prediction_active_status(stock_symbol)
            if active_status is None or active_status == 1:
                stock_data = download_stock_data(stock_symbol_yahoo)
                predicted_price = predict_algo(stock_data, stock_symbol)
                current_price = float(quote['currentValue'].replace(',', ''))
                logger.info(f"Predicted price: {predicted_price}, Current price: {current_price} for {quote.get('companyName')}")
                upsert_linear_prediction(
                    quote.get('companyName'),
                    stock_symbol,
                    current_price,
                    predicted_price,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    1
                )
            else:
                logger.warning(f"Stock {stock_symbol} is marked as inactive for {quote.get('companyName')}")

        except Exception as e:
            logger.error(f"Error predicting for {stock_symbol}: {str(e)}")
            if str(e) == "Inactive stock":
                set_linear_prediction_inactive(stock_symbol)

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
