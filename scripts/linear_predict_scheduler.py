import threading
import time

from flask import Flask, jsonify
import schedule
from bsedata.bse import BSE
from datetime import datetime
import logging

from scripts import create_db
from app.models.training_script import download_stock_data
from app.db.db_executor import execute_query
from app.utils.util import predict_algo, check_index_existence

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

scheduler = schedule.Scheduler()

def update_database():
    logger.info("Scheduler started")
    b = BSE()
    b.updateScripCodes()
    funds = b.getScripCodes()
    stock_symbol = None

    # if not check_index_existence('idx_security_id_linear', 'predictions_linear'):
    #     logger.error("Index idx_security_id_linear does not exist")
    #     return

    for code, name in funds.items():
        try:
            quote = b.getQuote(code)
            stock_symbol = quote.get('securityID')
            stock_symbol_yahoo = stock_symbol + '.BO'  # Assuming it's a BSE stock
            query = 'SELECT active FROM predictions_linear WHERE security_id = ?'
            row = execute_query(query, (stock_symbol,), fetchone=True)
            if row is None or row['active'] == 1:
                stock_data = download_stock_data(stock_symbol_yahoo)
                predicted_price = predict_algo(stock_data, stock_symbol)
                current_price = float(quote['currentValue'].replace(',', ''))  # Handle comma in numbers
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
            if e is not None or str(e) == "Inactive stock":
                query = 'UPDATE predictions_linear SET active = 0 WHERE security_id = ?'
                execute_query(query, (stock_symbol,), commit=True)

def job():
    logger.info("Starting the scheduled job...")
    update_database()
    logger.info("Scheduled job completed.")
    schedule_next_run()

def schedule_next_run():
    logger.info("Scheduling next run...")
    schedule.clear()
    logger.info("Cleared previous schedule.")
    schedule.every(1).minutes.do(job)

def run_scheduler():
    schedule_next_run()
    while True:
        schedule.run_pending()
        time.sleep(5)

# Start the scheduler in a separate thread
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

@app.route('/')
def index():
    return jsonify({"message": "Scheduler and Updater Service Running"}), 200

if __name__ == '__main__':
    create_db.create_db()
    app.run(host='0.0.0.0', port=5002, debug=True)
