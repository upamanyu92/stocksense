import time
import logging
import yfinance as yf
import pandas as pd
from typing import Dict, Any, Optional, List

def get_quote_with_retry(symbol: str, max_retries: int = 3, delay: int = 1) -> Optional[Dict[str, Any]]:
    """
    Get stock quote using yfinance with retry logic.
    
    Args:
        symbol: Stock symbol (e.g., 'RELIANCE.BO' for BSE stocks)
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
    
    Returns:
        Dictionary containing stock quote data in BSE-compatible format, or None if failed
    """
    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            ticker = yf.Ticker(symbol)
            
            # Try to get fast_info first (real-time data)
            try:
                fast_info = ticker.fast_info
                info = ticker.info
                
                # Map yfinance data to BSE-compatible format
                quote = {
                    'companyName': info.get('longName') or info.get('shortName') or symbol,
                    'securityID': symbol.replace('.BO', '').replace('.NS', ''),
                    'scripCode': info.get('symbol', symbol),
                    'currentValue': fast_info.get('lastPrice') or info.get('currentPrice') or info.get('regularMarketPrice', 0),
                    'change': fast_info.get('regularMarketChange') or info.get('regularMarketChange', 0),
                    'pChange': fast_info.get('regularMarketChangePercent') or info.get('regularMarketChangePercent', 0),
                    'dayHigh': fast_info.get('dayHigh') or info.get('dayHigh', 0),
                    'dayLow': fast_info.get('dayLow') or info.get('dayLow', 0),
                    'previousClose': fast_info.get('previousClose') or info.get('previousClose', 0),
                    'previousOpen': fast_info.get('open') or info.get('open', 0),
                    '52weekHigh': fast_info.get('yearHigh') or info.get('fiftyTwoWeekHigh', 0),
                    '52weekLow': fast_info.get('yearLow') or info.get('fiftyTwoWeekLow', 0),
                    'faceValue': info.get('bookValue', 0),
                    'group': info.get('quoteType', ''),
                    'industry': info.get('industry', ''),
                    'marketCapFull': info.get('marketCap', ''),
                    'marketCapFreeFloat': info.get('marketCap', ''),
                    'totalTradedQuantity': info.get('volume', ''),
                    'totalTradedValue': '',
                    'weightedAvgPrice': info.get('regularMarketPrice', 0),
                    '2WeekAvgQuantity': info.get('averageVolume', ''),
                    'updatedOn': pd.Timestamp.now().strftime('%d %b %y'),
                    'buy': {},
                    'sell': {}
                }
                
                # Check if we got meaningful data
                if quote.get('currentValue'):
                    return quote
            except Exception as e:
                logging.warning(f"Failed to get fast_info for {symbol}, trying info only: {e}")
                # Fallback to info only
                info = ticker.info
                if not info:
                    raise ValueError(f"No data available for {symbol}")
                
                quote = {
                    'companyName': info.get('longName') or info.get('shortName') or symbol,
                    'securityID': symbol.replace('.BO', '').replace('.NS', ''),
                    'scripCode': info.get('symbol', symbol),
                    'currentValue': info.get('currentPrice') or info.get('regularMarketPrice', 0),
                    'change': info.get('regularMarketChange', 0),
                    'pChange': info.get('regularMarketChangePercent', 0),
                    'dayHigh': info.get('dayHigh', 0),
                    'dayLow': info.get('dayLow', 0),
                    'previousClose': info.get('previousClose', 0),
                    'previousOpen': info.get('open', 0),
                    '52weekHigh': info.get('fiftyTwoWeekHigh', 0),
                    '52weekLow': info.get('fiftyTwoWeekLow', 0),
                    'faceValue': info.get('bookValue', 0),
                    'group': info.get('quoteType', ''),
                    'industry': info.get('industry', ''),
                    'marketCapFull': info.get('marketCap', ''),
                    'marketCapFreeFloat': info.get('marketCap', ''),
                    'totalTradedQuantity': info.get('volume', ''),
                    'totalTradedValue': '',
                    'weightedAvgPrice': info.get('regularMarketPrice', 0),
                    '2WeekAvgQuantity': info.get('averageVolume', ''),
                    'updatedOn': pd.Timestamp.now().strftime('%d %b %y'),
                    'buy': {},
                    'sell': {}
                }
                return quote
                
        except Exception as e:
            last_exception = e
            logging.warning(f"Attempt {attempt} failed for {symbol}: {e}")
        time.sleep(delay)
    
    logging.error(f"All {max_retries} attempts failed for {symbol}")
    if last_exception:
        raise last_exception
    return None


def get_indian_stocks() -> Dict[str, str]:
    """
    Get a list of Indian stocks traded on BSE and NSE.
    
    Returns:
        Dictionary mapping stock symbols to company names
    """
    import os
    
    logging.info("Fetching Indian stock list...")
    
    # Try to load from the existing stk.json file
    # First check in the root directory
    current_file = os.path.abspath(__file__)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    stock_file_path = os.path.join(base_dir, 'stk.json')
    
    if os.path.exists(stock_file_path):
        stocks = download_stock_list_from_file(stock_file_path)
        logging.info(f"Loaded {len(stocks)} Indian stocks from {stock_file_path}")
        return stocks
    
    # Fallback: try app/static/stk.json
    stock_file_path = os.path.join(base_dir, 'app', 'static', 'stk.json')
    if os.path.exists(stock_file_path):
        stocks = download_stock_list_from_file(stock_file_path)
        logging.info(f"Loaded {len(stocks)} Indian stocks from {stock_file_path}")
        return stocks
    
    # If no file found, return empty dict
    logging.warning(
        "No stock list file found. Please run scripts/download_stk_json.py first."
    )
    return {}


def verify_symbol(symbol: str) -> Optional[str]:
    """
    Verify if a stock symbol exists and return company name.
    
    Args:
        symbol: Stock symbol to verify (e.g., 'RELIANCE.BO')
    
    Returns:
        Company name if symbol exists, None otherwise
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if info and 'symbol' in info:
            return info.get('longName') or info.get('shortName')
        return None
    except Exception as e:
        logging.error(f"Error verifying symbol {symbol}: {e}")
        return None


def download_stock_list_from_file(file_path: str) -> Dict[str, str]:
    """
    Download stock list from a local file.
    This can be used to load stock symbols from a pre-existing list.
    
    Args:
        file_path: Path to JSON file containing stock mappings
    
    Returns:
        Dictionary mapping symbols to company names
    """
    import json
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading stock list from {file_path}: {e}")
        return {}


def get_nifty_stocks() -> List[Dict[str, str]]:
    """
    Get list of NIFTY index stocks.
    
    Returns:
        List of dictionaries with stock information
    """
    # Download NIFTY 50 constituents
    try:
        # This is a placeholder - in production, fetch from NSE or use a curated list
        nifty = []
        return nifty
    except Exception as e:
        logging.error(f"Error fetching NIFTY stocks: {e}")
        return []
