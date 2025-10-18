import time
import logging
from bsedata.bse import BSE

def get_quote_with_retry(code, max_retries=3, delay=1):
    """Get BSE quote with retry logic."""
    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            b = BSE()
            quote = b.getQuote(code)
            if quote:
                return quote
        except Exception as e:
            last_exception = e
            logging.warning(f"Attempt {attempt} failed for getQuote({code}): {e}")
        time.sleep(delay)
    logging.error(f"All {max_retries} attempts failed for getQuote({code})")
    if last_exception:
        raise last_exception
    return None

