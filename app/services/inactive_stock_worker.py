import threading
import time
import logging
import json
from datetime import datetime, timedelta

from app.db.session_manager import get_session_manager
from app.utils.yfinance_utils import get_quote_with_retry

class InactiveStockRetryWorker:
    """Worker to retry downloads for stocks marked as inactive."""
    def __init__(self, interval_minutes=60, retry_delay_hours=1):
        self.running = False
        self.worker_thread = None
        self.interval = interval_minutes * 60  # seconds
        self.retry_delay = retry_delay_hours  # hours
        self.lock = threading.Lock()
        self.stop_event = threading.Event()  # Add stop event for interruptible sleep

    def start(self):
        if self.running:
            return
        self.running = True
        self.stop_event.clear()  # Clear stop event
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logging.info("InactiveStockRetryWorker started")

    def stop(self):
        self.running = False
        self.stop_event.set()  # Signal the thread to wake up
        if self.worker_thread:
            self.worker_thread.join(timeout=10)  # Increased timeout
        logging.info("InactiveStockRetryWorker stopped")

    def _interruptible_sleep(self, seconds):
        """Sleep that can be interrupted by stop event"""
        self.stop_event.wait(timeout=seconds)
        return not self.running  # Return True if stopped

    def _worker_loop(self):
        logging.info("InactiveStockRetryWorker loop started")
        while self.running:
            try:
                self._retry_inactive_stocks()

                # Use interruptible sleep - check every 10 seconds
                remaining_time = self.interval
                while self.running and remaining_time > 0:
                    sleep_time = min(remaining_time, 10)
                    if self._interruptible_sleep(sleep_time):
                        break  # Stopped
                    remaining_time -= sleep_time

            except Exception as e:
                logging.error(f"Error in InactiveStockRetryWorker loop: {e}", exc_info=True)
                if self.running:
                    self._interruptible_sleep(60)  # Interruptible sleep on error too

    def _retry_inactive_stocks(self):
        db = get_session_manager()
        # Fetch all inactive stocks with their last_download_attempt and stock_symbol
        inactive_stocks = db.fetch_all(
            "SELECT security_id, company_name, scrip_code, stock_symbol, last_download_attempt "
            "FROM stock_quotes WHERE stock_status = 'inactive'"
        )
        logging.info(f"Retrying download for {len(inactive_stocks)} inactive stocks")
        now = datetime.now()
        retry_threshold = now - timedelta(hours=self.retry_delay)
        for stock in inactive_stocks:
            security_id = stock.get('security_id')
            company_name = stock.get('company_name')
            stock_symbol = stock.get('stock_symbol')
            last_attempt = stock.get('last_download_attempt')
            # Only retry if last_download_attempt is None or older than threshold
            if last_attempt:
                try:
                    last_attempt_dt = datetime.fromisoformat(last_attempt)
                except Exception:
                    last_attempt_dt = None
            else:
                last_attempt_dt = None
            if last_attempt_dt and last_attempt_dt > retry_threshold:
                logging.info(f"Skipping retry for {company_name} ({security_id}): last attempt at {last_attempt_dt.isoformat()} (threshold: {retry_threshold.isoformat()})")
                continue
            
            # Prefer stock_symbol, fallback to security_id with .BO
            if stock_symbol:
                symbol = stock_symbol
            elif security_id:
                symbol = security_id + '.BO'
            else:
                logging.warning(f"Skipping inactive stock {company_name} ({security_id}): no symbol available")
                continue
            
            try:
                quote = get_quote_with_retry(symbol)
                if quote:
                    self._update_stock_to_active(quote)
                    logging.info(f"Successfully reactivated stock {company_name} ({security_id})")
                else:
                    logging.warning(f"Retry failed for {company_name} ({security_id})")
            except Exception as e:
                logging.error(f"Error retrying inactive stock {company_name} ({security_id}): {e}")

    def _update_stock_to_active(self, quote):
        db = get_session_manager()
        try:
            current_value = quote.get('currentValue', 0)
            db.update('''
                UPDATE stock_quotes SET
                    company_name = ?,
                    current_value = ?,
                    change = ?,
                    p_change = ?,
                    day_high = ?,
                    day_low = ?,
                    previous_close = ?,
                    previous_open = ?,
                    two_week_avg_quantity = ?,
                    high_52week = ?,
                    low_52week = ?,
                    face_value = ?,
                    group_name = ?,
                    industry = ?,
                    market_cap_free_float = ?,
                    market_cap_full = ?,
                    total_traded_quantity = ?,
                    total_traded_value = ?,
                    updated_on = ?,
                    weighted_avg_price = ?,
                    buy = ?,
                    sell = ?,
                    stock_status = 'active',
                    download_attempts = 0,
                    last_download_attempt = ?
                WHERE security_id = ?
            ''', (
                quote.get('companyName'),
                float(current_value) if isinstance(current_value, (int, float)) else float(str(current_value).replace(',', '')),
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
                datetime.now().isoformat(),
                quote.get('securityID')
            ))
        except Exception as e:
            logging.error(f"Error updating stock to active: {e}. Raw quote: {quote}")

# Global instance
inactive_stock_worker = InactiveStockRetryWorker()
