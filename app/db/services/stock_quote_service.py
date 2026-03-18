"""
Stock Quote database service for managing stock_quotes table operations
"""
from typing import Optional, List, Dict, Any
import logging
from app.db.session_manager import get_session_manager
from app.db.data_models import StockQuote


class StockQuoteService:
    """Service for managing stock_quotes table operations"""
    
    @staticmethod
    def create(quote: StockQuote) -> Optional[int]:
        """Create a new stock quote"""
        db = get_session_manager()

        try:
            return db.insert('''
                INSERT OR REPLACE INTO stock_quotes (
                    company_name, current_value, change, p_change, updated_on,
                    security_id, scrip_code, group_type, face_value, industry,
                    previous_close, previous_open, day_high, day_low,
                    high_52week, low_52week, weighted_avg_price,
                    total_traded_value, total_traded_quantity, two_week_avg_quantity,
                    market_cap_full, market_cap_free_float, stock_status,
                    download_attempts, last_download_attempt
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                quote.company_name, quote.current_value, quote.change, quote.p_change,
                quote.updated_on, quote.security_id, quote.scrip_code, quote.group_type,
                quote.face_value, quote.industry, quote.previous_close, quote.previous_open,
                quote.day_high, quote.day_low, quote.high_52week, quote.low_52week,
                quote.weighted_avg_price, quote.total_traded_value, quote.total_traded_quantity,
                quote.two_week_avg_quantity, quote.market_cap_full, quote.market_cap_free_float,
                quote.stock_status or 'active', quote.download_attempts or 0,
                quote.last_download_attempt
            ))
        except Exception as e:
            logging.error(f"Error creating stock quote: {e}")
            return None

    @staticmethod
    def insert_from_dict(quote_dict: Dict[str, Any]) -> None:
        """Insert stock quote from dictionary (legacy support)"""
        db = get_session_manager()

        data = {
            'company_name': quote_dict.get('companyName', None),
            'current_value': float(quote_dict.get('currentValue', 0.0)),
            'change': float(quote_dict.get('change', 0.0)),
            'p_change': float(quote_dict.get('pChange', 0.0)),
            'updated_on': quote_dict.get('updatedOn', None),
            'security_id': quote_dict.get('securityID', None),
            'scrip_code': quote_dict.get('scripCode', None),
            'group_type': quote_dict.get('group', None),
            'face_value': float(quote_dict.get('faceValue', 0.0)),
            'industry': quote_dict.get('industry', None),
            'previous_close': float(quote_dict.get('previousClose', 0.0)),
            'previous_open': float(quote_dict.get('previousOpen', 0.0)),
            'day_high': float(quote_dict.get('dayHigh', 0.0)),
            'day_low': float(quote_dict.get('dayLow', 0.0)),
            'high_52week': float(quote_dict.get('52weekHigh', 0.0)),
            'low_52week': float(quote_dict.get('52weekLow', 0.0)),
            'weighted_avg_price': float(quote_dict.get('weightedAvgPrice', 0.0)),
            'total_traded_value': quote_dict.get('totalTradedValue', None),
            'total_traded_quantity': quote_dict.get('totalTradedQuantity', None),
            'two_week_avg_quantity': quote_dict.get('2WeekAvgQuantity', None),
            'market_cap_full': quote_dict.get('marketCapFull', None),
            'market_cap_free_float': quote_dict.get('marketCapFreeFloat', None)
        }
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        sql = f'INSERT OR REPLACE INTO stock_quotes ({columns}) VALUES ({placeholders})'
        
        try:
            db.insert(sql, tuple(data.values()))
        except Exception as e:
            logging.error(f"Error inserting stock quote: {e}")

    @staticmethod
    def get_by_id(quote_id: int) -> Optional[StockQuote]:
        """Get stock quote by ID"""
        db = get_session_manager()
        row = db.fetch_one('SELECT * FROM stock_quotes WHERE id = ?', (quote_id,))

        if row:
            return StockQuote(**row)
        return None
    
    @staticmethod
    def get_by_company_name(company_name: str) -> Optional[StockQuote]:
        """Get stock quote by company name"""
        db = get_session_manager()
        row = db.fetch_one('SELECT * FROM stock_quotes WHERE company_name = ?', (company_name,))

        if row:
            return StockQuote(**row)
        return None
    
    @staticmethod
    def search_by_name(company_name: str) -> List[Dict[str, Any]]:
        """Search stock quotes by company name pattern"""
        db = get_session_manager()
        return db.fetch_all('SELECT * FROM stock_quotes WHERE company_name LIKE ?', (f'%{company_name}%',))

    @staticmethod
    def get_batch(limit: int, offset: int) -> List[StockQuote]:
        """Get a batch of stock quotes"""
        db = get_session_manager()
        rows = db.fetch_all('SELECT * FROM stock_quotes LIMIT ? OFFSET ?', (limit, offset))
        return [StockQuote(**row) for row in rows]

    @staticmethod
    def get_all() -> List[StockQuote]:
        """Get all stock quotes"""
        db = get_session_manager()
        rows = db.fetch_all('SELECT * FROM stock_quotes')
        return [StockQuote(**row) for row in rows]

    @staticmethod
    def count() -> int:
        """Get total count of stock quotes"""
        db = get_session_manager()
        row = db.fetch_one('SELECT COUNT(*) as count FROM stock_quotes')
        return row['count'] if row else 0

