from typing import Optional, List, Dict, Any
import sqlite3

from app.db.data_models import StockQuote
from app.config import Config
import logging
from datetime import datetime
import threading

from bsedata.bse import BSE
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_db_connection() -> sqlite3.Connection:
    Config.ensure_directories()
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_one(query: str, args: tuple = ()) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, args)
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"An error occurred while fetching one: {e}")
        return None
    finally:
        conn.close()

def fetch_all(query: str, args: tuple = ()) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, args)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"An error occurred while fetching all: {e}")
    finally:
        conn.close()


def data_retriever_executor(status_queue, max_workers=4):
    status_queue.put(f"data_retriever_executor: started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"data_retriever_executor: started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    b = BSE()
    b.updateScripCodes()
    trade_funds = b.getScripCodes()
    total_funds = len(trade_funds)
    codes_list = list(trade_funds.items())
    counter = {'done': 0}

    def process_stock(code_name):
        code, name = code_name
        try:
            company_name = b.verifyScripCode(code)
            existing_quote = fetch_one('SELECT * FROM stock_quotes WHERE company_name = ?', (company_name,))
            if (not company_name) or (company_name != name):
                msg = f"{name} - skipped - name mismatch or not found"
                logging.info(msg)
                status_queue.put(msg)
                return
            else:
                logging.debug(f"Processing {name} with code {code}")
                if existing_quote:
                    logging.debug(f"Updating existing quote for {name}")
                    # quote = b.getQuote(code)
                    # update_stock_quote(quote)
                else:
                    quote = b.getQuote(code)
                    insert_stock_quote(quote)
            # Thread-safe increment
            done = None
            from threading import Lock
            if not hasattr(process_stock, 'lock'):
                process_stock.lock = Lock()
            with process_stock.lock:
                counter['done'] += 1
                done = counter['done']
            msg = f"{name} - completed - {total_funds-done}/{total_funds}"
            logging.info(f"{msg} [Thread: {threading.current_thread().name}]")
            status_queue.put(msg)
        except Exception as e:
            logging.debug(f"Downloading failed {code}: {e}")
            status_queue.put(f"{name} - failed: {e}")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_stock, code_name) for code_name in codes_list]
        for _ in as_completed(futures):
            pass  # All status is handled in process_stock

def execute_query(query: str, args: tuple = (), fetchone: bool = False, fetchall: bool = False, commit: bool = False) -> Optional[Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, args)
        if commit:
            conn.commit()
        if fetchone:
            result = cursor.fetchone()
        elif fetchall:
            result = cursor.fetchall()
        else:
            result = None
    except Exception as e:
        print(f"An error occurred while executing query: {query}: {e}")
        result = None
    finally:
        conn.close()
    return result

def fetch_quotes_batch(limit: int, offset: int) -> List[StockQuote]:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM stock_quotes LIMIT ? OFFSET ?', (limit, offset))
    rows = c.fetchall()
    conn.close()
    return [StockQuote(**dict(row)) for row in rows]

def fetch_quotes(company_name: str) -> Dict[str, Any]:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM stock_quotes WHERE company_name LIKE ?', (f'%{company_name}%',))
    rows = c.fetchall()
    conn.close()
    return {"quotes": [dict(row) for row in rows]}

def insert_stock_quote(quote: Dict[str, Any]) -> None:
    conn = get_db_connection()
    c = conn.cursor()

    data = {
        'company_name': quote.get('companyName', None),
        'current_value': float(quote.get('currentValue', 0.0)),
        'change': float(quote.get('change', 0.0)),
        'p_change': float(quote.get('pChange', 0.0)),
        'updated_on': quote.get('updatedOn', None),
        'security_id': quote.get('securityID', None),
        'scrip_code': quote.get('scripCode', None),
        'group_type': quote.get('group', None),
        'face_value': float(quote.get('faceValue', 0.0)),
        'industry': quote.get('industry', None),
        'previous_close': float(quote.get('previousClose', 0.0)),
        'previous_open': float(quote.get('previousOpen', 0.0)),
        'day_high': float(quote.get('dayHigh', 0.0)),
        'day_low': float(quote.get('dayLow', 0.0)),
        'week_52_high': float(quote.get('52weekHigh', 0.0)),
        'week_52_low': float(quote.get('52weekLow', 0.0)),
        'weighted_avg_price': float(quote.get('weightedAvgPrice', 0.0)),
        'total_traded_value': quote.get('totalTradedValue', None),
        'total_traded_quantity': quote.get('totalTradedQuantity', None),
        'two_week_avg_quantity': quote.get('2WeekAvgQuantity', None),
        'market_cap_full': quote.get('marketCapFull', None),
        'market_cap_free_float': quote.get('marketCapFreeFloat', None)
    }

    columns = ', '.join(data.keys())
    placeholders = ', '.join(['?' for _ in data])
    sql = f'''
        INSERT OR REPLACE INTO stock_quotes ({columns})
        VALUES ({placeholders})
    '''

    try:
        c.execute(sql, list(data.values()))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error inserting stock quote: {e}")
    finally:
        conn.close()


def update_stock_quote(quote: Dict[str, Any]) -> None:
    conn = get_db_connection()
    c = conn.cursor()

    data = {
        'company_name': quote.get('companyName', None),
        'current_value': float(quote.get('currentValue', 0.0)),
        'change': float(quote.get('change', 0.0)),
        'p_change': float(quote.get('pChange', 0.0)),
        'updated_on': quote.get('updatedOn', None),
        'scrip_code': quote.get('scripCode', None),
        'group_type': quote.get('group', None),
        'face_value': float(quote.get('faceValue', 0.0)),
        'industry': quote.get('industry', None),
        'previous_close': float(quote.get('previousClose', 0.0)),
        'previous_open': float(quote.get('previousOpen', 0.0)),
        'day_high': float(quote.get('dayHigh', 0.0)),
        'day_low': float(quote.get('dayLow', 0.0)),
        'week_52_high': float(quote.get('52weekHigh', 0.0)),
        'week_52_low': float(quote.get('52weekLow', 0.0)),
        'weighted_avg_price': float(quote.get('weightedAvgPrice', 0.0)),
        'total_traded_value': quote.get('totalTradedValue', None),
        'total_traded_quantity': quote.get('totalTradedQuantity', None),
        'two_week_avg_quantity': quote.get('2WeekAvgQuantity', None),
        'market_cap_full': quote.get('marketCapFull', None),
        'market_cap_free_float': quote.get('marketCapFreeFloat', None)
    }

    set_clause = ', '.join([f"{key} = ?" for key in data.keys() if key != 'security_id'])
    sql = f'''
        UPDATE stock_quotes
        SET {set_clause}
        WHERE security_id = ?
    '''

    try:
        c.execute(sql, list(data.values()) + [quote.get('securityID')])
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error updating stock quote: {e}")
    finally:
        conn.close()

def get_prediction_by_security_id(security_id: str):
    return fetch_one('SELECT * FROM predictions WHERE security_id = ?', (security_id,))

def upsert_prediction(company_name: str, security_id: str, current_price: float, predicted_price: float, prediction_date: str):
    row = get_prediction_by_security_id(security_id)
    if row:
        execute_query('''
            UPDATE predictions
            SET company_name = ?, current_price = ?, predicted_price = ?, prediction_date = ?
            WHERE security_id = ?
        ''', (company_name, current_price, predicted_price, prediction_date, security_id), commit=True)
    else:
        execute_query('''
            INSERT INTO predictions (company_name, security_id, current_price, predicted_price, prediction_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (company_name, security_id, current_price, predicted_price, prediction_date), commit=True)

def get_linear_prediction_active_status(security_id: str):
    row = fetch_one('SELECT active FROM predictions_linear WHERE security_id = ?', (security_id,))
    return row['active'] if row else None

def upsert_linear_prediction(company_name: str, security_id: str, current_price: float, predicted_price: float, prediction_date: str, active: int = 1):
    execute_query('''
        INSERT INTO predictions_linear (company_name, security_id, current_price, predicted_price, prediction_date, active)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(security_id) DO UPDATE SET
            company_name=excluded.company_name,
            current_price=excluded.current_price,
            predicted_price=excluded.predicted_price,
            prediction_date=excluded.prediction_date,
            active=excluded.active
    ''', (company_name, security_id, current_price, predicted_price, prediction_date, active), commit=True)

def set_linear_prediction_inactive(security_id: str):
    execute_query('UPDATE predictions_linear SET active = 0 WHERE security_id = ?', (security_id,), commit=True)

def get_configuration(symbol: str, model_type: str = 'transformer'):
    query = '''
        SELECT * FROM model_configurations 
        WHERE symbol = ? AND model_type = ?
        ORDER BY updated_at DESC LIMIT 1
    '''
    return fetch_one(query, (symbol, model_type))

def get_all_configurations():
    query = "SELECT * FROM model_configurations ORDER BY updated_at DESC"
    return fetch_all(query)

def create_configuration(config):
    now = datetime.now()
    config.created_at = now
    config.updated_at = now
    query = '''
        INSERT INTO model_configurations (
            symbol, model_type, num_heads, ff_dim, dropout_rate,
            learning_rate, batch_size, epochs, sequence_length,
            early_stopping_patience, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    params = (
        config.symbol, config.model_type, config.num_heads,
        config.ff_dim, config.dropout_rate, config.learning_rate,
        config.batch_size, config.epochs, config.sequence_length,
        config.early_stopping_patience, config.created_at,
        config.updated_at
    )
    config.id = execute_query(query, params)
    return config

def update_configuration(config):
    config.updated_at = datetime.now()
    query = '''
        UPDATE model_configurations SET
            num_heads = ?,
            ff_dim = ?,
            dropout_rate = ?,
            learning_rate = ?,
            batch_size = ?,
            epochs = ?,
            sequence_length = ?,
            early_stopping_patience = ?,
            updated_at = ?
        WHERE id = ?
    '''
    params = (
        config.num_heads, config.ff_dim, config.dropout_rate,
        config.learning_rate, config.batch_size, config.epochs,
        config.sequence_length, config.early_stopping_patience,
        config.updated_at, config.id
    )
    execute_query(query, params)
    return config

def delete_configuration(config_id: int) -> bool:
    query = "DELETE FROM model_configurations WHERE id = ?"
    return execute_query(query, (config_id,)) > 0

def get_recent_predictions_for_monitor(cutoff_date):
    query = '''
        SELECT 
            symbol,
            current_price,
            predicted_price,
            actual_price,
            prediction_date,
            model_type
        FROM predictions
        WHERE prediction_date >= ?
        AND actual_price IS NOT NULL
    '''
    return fetch_all(query, (cutoff_date,))

def check_index_existence(index_name: str, table_name: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'")
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def get_top_stocks():
    query = '''
        SELECT company_name, security_id, current_price, predicted_price, 
               (predicted_price - current_price) AS profit,
               prediction_date
        FROM predictions
        ORDER BY (predicted_price - current_price) / current_price DESC
    '''
    rows = fetch_all(query)
    stocks = []
    for row in rows:
        stock = dict(row)
        stock['profit_percentage'] = ((stock['predicted_price'] - stock['current_price']) / stock['current_price']) * 100
        stocks.append(stock)
    return stocks
