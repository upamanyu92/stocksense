import threading
import time

from flask import Flask, jsonify
import schedule
import yfinance as yf
from datetime import datetime
import logging

from scripts import create_db
from app.models.training_script import download_stock_data
from app.db.db_executor import execute_query
from app.utils.util import predict_algo, check_index_existence
from app.utils.yfinance_utils import get_quote_with_retry

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

scheduler = schedule.Scheduler()

def update_database():
    logger.info("Scheduler started")
    
    # Load stock list from existing stk.json
    import json
    import os
    
    stock_file_path = os.path.join(os.path.dirname(__file__), '..', 'stk.json')
    try:
        with open(stock_file_path, 'r') as f:
            funds = json.load(f)
    except FileNotFoundError:
        logger.error("Stock list file not found")
        return
    
    stock_symbol = None

    # if not check_index_existence('idx_security_id_linear', 'predictions_linear'):
    #     logger.error("Index idx_security_id_linear does not exist")
    #     return

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
