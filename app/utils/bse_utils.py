import time
import logging
import yfinance as yf
import pandas as pd
from typing import Dict, Any, Optional

def get_quote_with_retry(symbol, max_retries=3, delay=1):
    """Get stock quote using yfinance with retry logic."""
    # Import from new yfinance utils
    from app.utils.yfinance_utils import get_quote_with_retry as yf_get_quote
    return yf_get_quote(symbol, max_retries, delay)

