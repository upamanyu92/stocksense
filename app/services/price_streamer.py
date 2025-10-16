"""
Real-time stock price streaming service.
Fetches and streams live stock price updates via WebSocket.
"""
import logging
import threading
import time
from datetime import datetime
from typing import List, Dict, Any

from bsedata.bse import BSE

from app.utils.util import get_db_connection


class StockPriceStreamer:
    """Manages real-time stock price streaming"""
    
    def __init__(self):
        self.websocket_manager = None
        self.streaming = False
        self.stream_thread = None
        self.watched_symbols = set()
        self.update_interval = 10  # Update every 10 seconds
        self.lock = threading.Lock()
        
    def set_websocket_manager(self, manager):
        """Set the websocket manager instance"""
        self.websocket_manager = manager
        
    def add_symbol(self, symbol: str):
        """Add a symbol to watch for price updates"""
        with self.lock:
            self.watched_symbols.add(symbol)
            logging.info(f"Added {symbol} to price streaming watchlist")
            
    def remove_symbol(self, symbol: str):
        """Remove a symbol from price watching"""
        with self.lock:
            self.watched_symbols.discard(symbol)
            logging.info(f"Removed {symbol} from price streaming watchlist")
            
    def get_watched_symbols(self) -> List[str]:
        """Get list of currently watched symbols"""
        with self.lock:
            return list(self.watched_symbols)
    
    def start_streaming(self):
        """Start the price streaming service"""
        if self.streaming:
            logging.warning("Price streaming already running")
            return
            
        self.streaming = True
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()
        logging.info("Stock price streaming started")
    
    def stop_streaming(self):
        """Stop the price streaming service"""
        self.streaming = False
        if self.stream_thread:
            self.stream_thread.join(timeout=5)
        logging.info("Stock price streaming stopped")
    
    def _stream_loop(self):
        """Main streaming loop"""
        logging.info("Price streaming loop started")
        
        while self.streaming:
            try:
                symbols = self.get_watched_symbols()
                
                if symbols:
                    # Fetch prices for watched symbols
                    self._fetch_and_emit_prices(symbols)
                
                # Wait before next update
                time.sleep(self.update_interval)
                
            except Exception as e:
                logging.error(f"Error in price streaming loop: {e}", exc_info=True)
                time.sleep(30)  # Wait longer on error
    
    def _fetch_and_emit_prices(self, symbols: List[str]):
        """Fetch current prices and emit via WebSocket"""
        b = BSE()
        
        for symbol in symbols:
            try:
                # Get stock info from database to find BSE code
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT security_id, company_name FROM stock_quotes 
                    WHERE stock_symbol = ? OR security_id = ?
                    LIMIT 1
                ''', (symbol, symbol))
                stock = cursor.fetchone()
                conn.close()
                
                if not stock:
                    logging.warning(f"Stock not found in database: {symbol}")
                    continue
                
                # Fetch live quote
                quote = b.getQuote(stock['security_id'])
                
                if quote:
                    # Extract price data
                    price_data = {
                        'symbol': symbol,
                        'security_id': stock['security_id'],
                        'company_name': quote.get('companyName', stock['company_name']),
                        'price': float(quote.get('currentValue', 0).replace(',', '') if isinstance(quote.get('currentValue'), str) else quote.get('currentValue', 0)),
                        'change': float(quote.get('change', 0)),
                        'pChange': float(quote.get('pChange', 0)),
                        'dayHigh': float(quote.get('dayHigh', 0)),
                        'dayLow': float(quote.get('dayLow', 0)),
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Emit price update via WebSocket
                    if self.websocket_manager:
                        self.websocket_manager.emit_stock_price_update(price_data)
                    
                    logging.debug(f"Streamed price update for {symbol}: {price_data['price']}")
                    
            except Exception as e:
                logging.error(f"Error fetching price for {symbol}: {e}")
    
    def fetch_price_once(self, symbol: str) -> Dict[str, Any]:
        """Fetch price for a single symbol immediately"""
        try:
            b = BSE()
            
            # Get stock info from database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT security_id, company_name FROM stock_quotes 
                WHERE stock_symbol = ? OR security_id = ?
                LIMIT 1
            ''', (symbol, symbol))
            stock = cursor.fetchone()
            conn.close()
            
            if not stock:
                return None
            
            # Fetch live quote
            quote = b.getQuote(stock['security_id'])
            
            if quote:
                price_data = {
                    'symbol': symbol,
                    'security_id': stock['security_id'],
                    'company_name': quote.get('companyName', stock['company_name']),
                    'price': float(quote.get('currentValue', 0).replace(',', '') if isinstance(quote.get('currentValue'), str) else quote.get('currentValue', 0)),
                    'change': float(quote.get('change', 0)),
                    'pChange': float(quote.get('pChange', 0)),
                    'dayHigh': float(quote.get('dayHigh', 0)),
                    'dayLow': float(quote.get('dayLow', 0)),
                    'timestamp': datetime.now().isoformat()
                }
                
                return price_data
                
        except Exception as e:
            logging.error(f"Error fetching price for {symbol}: {e}")
            return None


# Global price streamer instance
price_streamer = StockPriceStreamer()
