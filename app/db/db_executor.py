import sqlite3
from typing import List, Dict, Any, Optional
from app.utils.util import get_db_connection
from app.db.data_models import StockQuote
from app.db.services.stock_quote_service import StockQuoteService

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
        return []
    finally:
        conn.close()

def fetch_quotes_batch(limit: int, offset: int) -> List[StockQuote]:
    """Fetch a batch of stock quotes using the service layer"""
    return StockQuoteService.get_batch(limit, offset)

def fetch_quotes(company_name: str) -> Dict[str, Any]:
    """Search for stock quotes by company name using the service layer"""
    quotes = StockQuoteService.search_by_name(company_name)
    return {"quotes": quotes}

def insert_stock_quote(quote: Dict[str, Any]) -> None:
    """Insert stock quote from dictionary using the service layer"""
    StockQuoteService.insert_from_dict(quote)


def update_stock_quote(quote: Dict[str, Any]) -> None:
    conn = get_db_connection()
    c = conn.cursor()

    # Map dictionary keys to database column names
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
        'high_52week': float(quote.get('52weekHigh', 0.0)),
        'low_52week': float(quote.get('52weekLow', 0.0)),
        'weighted_avg_price': float(quote.get('weightedAvgPrice', 0.0)),
        'total_traded_value': quote.get('totalTradedValue', None),
        'total_traded_quantity': quote.get('totalTradedQuantity', None),
        'two_week_avg_quantity': quote.get('2WeekAvgQuantity', None),
        'market_cap_full': quote.get('marketCapFull', None),
        'market_cap_free_float': quote.get('marketCapFreeFloat', None)
    }

    set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
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

def get_predictions(security_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM predictions WHERE security_id = ?', (security_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]
