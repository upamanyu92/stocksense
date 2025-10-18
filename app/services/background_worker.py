"""
Background worker service for automated stock downloads and predictions.
"""
import concurrent
import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, Any

from bsedata.bse import BSE

from app.services.prediction_service import prediction_executor
from app.services.worker_settings_service import WorkerSettingsService
from app.utils.util import get_db_connection
from app.utils.bse_utils import get_quote_with_retry

# Import websocket_manager - will be set from main.py to avoid circular imports
websocket_manager = None

def set_websocket_manager(manager):
    """Set the websocket manager instance"""
    global websocket_manager
    websocket_manager = manager


class BackgroundWorker:
    """Background worker for automated stock processing"""
    
    def __init__(self):
        self.running = False
        self.worker_thread = None
        self.status_queue = queue.Queue()
        self.prediction_interval = 300  # Run predictions every 5 minutes
        self.lock = threading.Lock()
        self.last_run_date = None  # Track last run date for daily job

    def start(self):
        """Start the background worker"""
        # Check if worker is enabled in database configuration
        if not WorkerSettingsService.is_worker_enabled(WorkerSettingsService.BACKGROUND_WORKER):
            logging.info("Background worker is disabled in configuration, not starting")
            return
        
        if self.running:
            # logging.warning("Background worker already running")
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logging.info("Background worker started")
    
    def stop(self):
        """Stop the background worker"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logging.info("Background worker stopped")
    
    def _worker_loop(self):
        """Main worker loop"""
        logging.info("Background worker loop started")
        
        while self.running:
            try:
                # Check if worker is still enabled
                if not WorkerSettingsService.is_worker_enabled(WorkerSettingsService.BACKGROUND_WORKER):
                    logging.info("Background worker disabled in configuration, stopping")
                    self.running = False
                    break
                
                today = datetime.now().date()
                if self.last_run_date == today:
                    logging.info("Background worker already ran today. Sleeping until next day.")
                    # Sleep until next day (midnight)
                    now = datetime.now()
                    next_day = datetime.combine(now.date(), datetime.min.time()) + timedelta(days=1)
                    sleep_seconds = (next_day - now).total_seconds()
                    time.sleep(max(sleep_seconds, 60))
                    continue

                # Download stock quotes
                self._download_stocks()

                # Run predictions on active stocks
                self._run_predictions()
                
                self.last_run_date = today

                # Wait before next cycle
                time.sleep(self.prediction_interval)
                
            except Exception as e:
                logging.error(f"Error in background worker loop: {e}", exc_info=True)
                time.sleep(60)  # Wait a minute before retrying on error
    
    def _download_stocks(self):
        """Download stock quotes without timeout handling, with real-time status updates"""
        logging.info("Starting automated stock download")
        status_update = {
            'type': 'download',
            'status': 'started',
            'timestamp': datetime.now().isoformat()
        }
        self.status_queue.put(status_update)
        if websocket_manager:
            websocket_manager.emit_background_worker_status(status_update)

        try:
            b = BSE()
            b.updateScripCodes()
            funds = b.getScripCodes()

            total_stocks = len(funds)
            processed = 0
            failed = 0
            remaining = total_stocks

            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_code = {
                    executor.submit(self._download_single_stock, code, name, processed, remaining): (code, name) for
                    code, name in funds.items()}
                for future in concurrent.futures.as_completed(future_to_code):
                    code, name = future_to_code[future]
                    try:
                        future.result()  # Removed timeout
                        processed += 1
                        remaining -= 1
                    except Exception as e:
                        logging.error(f"Error downloading stock {name} ({code}): {e}")
                        self._mark_stock_inactive(code, name, str(e))
                        failed += 1
                        remaining -= 1

                    # Update progress for each stock (use company name)
                    progress_update = {
                        'type': 'download',
                        'status': 'progress',
                        'processed': processed,
                        'total': total_stocks,
                        'failed': failed,
                        'remaining': remaining,
                        'current_stock': name,  # <-- use company name
                        'timestamp': datetime.now().isoformat()
                    }
                    self.status_queue.put(progress_update)
                    if websocket_manager:
                        websocket_manager.emit_background_worker_status(progress_update)

            completion_update = {
                'type': 'download',
                'status': 'completed',
                'processed': processed,
                'failed': failed,
                'timestamp': datetime.now().isoformat()
            }
            self.status_queue.put(completion_update)
            if websocket_manager:
                websocket_manager.emit_background_worker_status(completion_update)

        except Exception as e:
            logging.error(f"Error in stock download: {e}", exc_info=True)
            error_update = {
                'type': 'download',
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self.status_queue.put(error_update)
            if websocket_manager:
                websocket_manager.emit_background_worker_status(error_update)

    def _download_single_stock(self, code: str, name: str, processed: int = 0, remaining: int = 0):
        """Download data for a single stock, emit status before and after"""
        # Emit status before processing (use company name)
        self.status_queue.put({
            'type': 'download',
            'status': 'processing',
            'current_stock': name,  # <-- use company name
            'processed': processed,
            'remaining': remaining,
            'timestamp': datetime.now().isoformat()
        })
        try:
            quote = get_quote_with_retry(code)

            if not quote:
                raise ValueError("No quote data returned")

            # Store quote in database
            self._store_stock_quote(quote)

            # Reset download attempts on success
            self._reset_download_attempts(quote.get('securityID'))

            logging.debug(f"Successfully downloaded {name}")

        except Exception as e:
            logging.error(f"Error downloading single stock {name}: {e}")
            raise

    def _store_stock_quote(self, quote: Dict[str, Any]):
        """Store stock quote in database"""
        import json
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO stock_quotes (
                    company_name, security_id, scrip_code, stock_symbol, current_value, change, p_change,
                    day_high, day_low, previous_close, previous_open, two_week_avg_quantity, high_52week, low_52week,
                    face_value, group_name, industry, market_cap_free_float, market_cap_full, total_traded_quantity,
                    total_traded_value, updated_on, weighted_avg_price, buy, sell, stock_status, last_download_attempt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
            ''', (
                quote.get('companyName'),
                quote.get('securityID'),
                quote.get('scripCode'),
                quote.get('securityID'),  # stock_symbol fallback
                float(quote.get('currentValue', 0).replace(',', '') if isinstance(quote.get('currentValue'), str) else quote.get('currentValue', 0)),
                float(quote.get('change', 0)),
                float(quote.get('pChange', 0)),
                float(quote.get('dayHigh', 0)),
                float(quote.get('dayLow', 0)),
                float(quote.get('previousClose', 0)),
                float(quote.get('previousOpen', 0)),
                quote.get('2WeekAvgQuantity'),
                float(quote.get('52weekHigh', 0)),
                float(quote.get('52weekLow', 0)),
                float(quote.get('faceValue', 0)),
                quote.get('group'),
                quote.get('industry'),
                quote.get('marketCapFreeFloat'),
                quote.get('marketCapFull'),
                quote.get('totalTradedQuantity'),
                quote.get('totalTradedValue'),
                quote.get('updatedOn'),
                float(quote.get('weightedAvgPrice', 0)),
                json.dumps(quote.get('buy', {})),
                json.dumps(quote.get('sell', {})),
                datetime.now().isoformat()
            ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logging.error(f"Error storing stock quote: {e}. Raw quote: {quote}")
            raise
        finally:
            conn.close()
    
    def _mark_stock_inactive(self, code: str, name: str, reason: str):
        """Mark a stock as inactive after download failure"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Update or insert stock status
            cursor.execute('''
                INSERT INTO stock_quotes (
                    company_name, security_id, stock_status, scrip_code,
                    download_attempts, last_download_attempt
                )
                VALUES (?, ?, ?, 'inactive', 1, ?)
                ON CONFLICT(security_id) DO UPDATE SET
                    stock_status = 'inactive',
                    download_attempts = download_attempts + 1,
                    last_download_attempt = ?
            ''', (name, code, code, datetime.now().isoformat(), datetime.now().isoformat()))
            conn.commit()
            
            logging.warning(f"Marked stock {name} (code: {code}) as inactive. Reason: {reason}")
            
        except Exception as e:
            conn.rollback()
            logging.error(f"Error marking stock inactive: {e}")
        finally:
            conn.close()
    
    def _reset_download_attempts(self, security_id: str):
        """Reset download attempts counter on successful download"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE stock_quotes 
                SET download_attempts = 0,
                    stock_status = 'active'
                WHERE security_id = ?
            ''', (security_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logging.error(f"Error resetting download attempts: {e}")
        finally:
            conn.close()
    
    def _run_predictions(self):
        """Run predictions on watchlist stocks only"""
        logging.info("Starting automated predictions on watchlist stocks")
        start_update = {
            'type': 'prediction',
            'status': 'started',
            'timestamp': datetime.now().isoformat()
        }
        self.status_queue.put(start_update)
        if websocket_manager:
            websocket_manager.emit_background_worker_status(start_update)
        
        # Get watchlist stocks from all users
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT sq.* 
            FROM stock_quotes sq
            INNER JOIN user_watchlist uw ON sq.stock_symbol = uw.stock_symbol OR sq.security_id = uw.stock_symbol
            WHERE sq.stock_status = 'active'
            ORDER BY sq.company_name
        ''')
        watchlist_stocks = cursor.fetchall()
        conn.close()
        
        total = len(watchlist_stocks)
        processed = 0
        
        logging.info(f"Found {total} unique stocks in watchlists to process")
        
        for stock in watchlist_stocks:
            if not self.running:
                break
            
            try:
                # Run prediction
                prediction_executor(dict(stock))
                processed += 1
                
                # Update progress
                if processed % 5 == 0:
                    progress_update = {
                        'type': 'prediction',
                        'status': 'progress',
                        'processed': processed,
                        'total': total,
                        'stock_name': stock['company_name'],
                        'timestamp': datetime.now().isoformat()
                    }
                    self.status_queue.put(progress_update)
                    if websocket_manager:
                        websocket_manager.emit_background_worker_status(progress_update)
                    
            except Exception as e:
                logging.error(f"Error predicting for {stock['company_name']}: {e}")
        
        completion_update = {
            'type': 'prediction',
            'status': 'completed',
            'processed': processed,
            'total': total,
            'timestamp': datetime.now().isoformat()
        }
        self.status_queue.put(completion_update)
        if websocket_manager:
            websocket_manager.emit_background_worker_status(completion_update)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current worker status"""
        statuses = []
        while not self.status_queue.empty():
            try:
                statuses.append(self.status_queue.get_nowait())
            except queue.Empty:
                break
        
        return {
            'running': self.running,
            'recent_updates': statuses[-10:] if statuses else []
        }


# Global worker instance
background_worker = BackgroundWorker()
