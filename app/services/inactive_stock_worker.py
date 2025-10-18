import threading
import time
import logging
from datetime import datetime, timedelta
from app.services.worker_settings_service import WorkerSettingsService
from app.utils.util import get_db_connection
from app.utils.bse_utils import get_quote_with_retry


class InactiveStockRetryWorker:
    """Worker to retry downloads for stocks marked as inactive."""
    def __init__(self, interval_minutes=60, retry_delay_hours=1):
        self.running = False
        self.worker_thread = None
        self.interval = interval_minutes * 60  # seconds
        self.retry_delay = retry_delay_hours  # hours
        self.lock = threading.Lock()

    def start(self):
        # Check if worker is enabled in database configuration
        if not WorkerSettingsService.is_worker_enabled(WorkerSettingsService.INACTIVE_STOCK_WORKER):
            logging.info("InactiveStockRetryWorker is disabled in configuration, not starting")
            return

        if self.running:
            return
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logging.info("InactiveStockRetryWorker started")

    def stop(self):
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logging.info("InactiveStockRetryWorker stopped")

    def _worker_loop(self):
        logging.info("InactiveStockRetryWorker loop started")
        while self.running:
            try:
                # Check if worker is still enabled
                if not WorkerSettingsService.is_worker_enabled(WorkerSettingsService.INACTIVE_STOCK_WORKER):
                    logging.info("InactiveStockRetryWorker disabled in configuration, stopping")
                    self.running = False
                    break

                self._retry_inactive_stocks()
                time.sleep(self.interval)
            except Exception as e:
                logging.error(f"Error in InactiveStockRetryWorker loop: {e}", exc_info=True)
                time.sleep(60)

    def _retry_inactive_stocks(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        # Fetch all inactive stocks with their last_download_attempt
        cursor.execute(
            "SELECT security_id, company_name, scrip_code, "
            "last_download_attempt FROM stock_quotes "
            "WHERE stock_status = 'inactive'")
        inactive_stocks = cursor.fetchall()
        conn.close()
        logging.info(f"Retrying download for {len(inactive_stocks)} inactive stocks")
        now = datetime.now()
        retry_threshold = now - timedelta(hours=self.retry_delay)
        for stock in inactive_stocks:
            security_id = stock['security_id']
            company_name = stock['company_name']
            scrip_code = stock['scrip_code']
            last_attempt = stock['last_download_attempt']
            # Only retry if last_download_attempt is None or older than threshold
            if last_attempt:
                try:
                    last_attempt_dt = datetime.fromisoformat(last_attempt)
                except Exception:
                    last_attempt_dt = None
            else:
                last_attempt_dt = None
            if last_attempt_dt and last_attempt_dt > retry_threshold:
                logging.info(
                    f"Skipping retry for {company_name} ({security_id}): "
                    f"last attempt at {last_attempt_dt.isoformat()} "
                    f"(threshold: {retry_threshold.isoformat()})")
                continue
            if not scrip_code:
                logging.warning(f"Skipping inactive stock {company_name} ({security_id}): missing scrip_code")
                continue
            try:
                quote = get_quote_with_retry(scrip_code)
                if quote:
                    self._update_stock_to_active(quote)
                    logging.info(f"Successfully reactivated stock {company_name} ({security_id})")
                else:
                    logging.warning(f"Retry failed for {company_name} ({security_id})")
            except Exception as e:
                logging.error(f"Error retrying inactive stock {company_name} ({security_id}): {e}")

    def _update_stock_to_active(self, quote):
        import json
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
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
                float(quote.get('currentValue', 0).replace(',', '') if isinstance(
                    quote.get('currentValue'), str) else quote.get('currentValue', 0)),
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
            conn.commit()
        except Exception as e:
            conn.rollback()
            logging.error(f"Error updating stock to active: {e}. Raw quote: {quote}")
        finally:
            conn.close()


# Global instance
inactive_stock_worker = InactiveStockRetryWorker()
