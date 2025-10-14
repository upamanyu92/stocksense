import logging
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional, List, Dict, Any

from bsedata.bse import BSE

from app.db.data_models import StockQuote
from app.utils.util import get_db_connection


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
                    logging.debug(f"Calling b.getQuote for {name} with code {code}")
                    quote = b.getQuote(code)
                    logging.debug(f"Quote received for {name}: {quote}")
                    insert_stock_quote(quote)
                    logging.debug(f"Inserted quote for {name}")
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
        logging.error(f"Error inserting stock quote: {e}")
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