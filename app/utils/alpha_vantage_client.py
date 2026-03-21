"""
Alpha Vantage MCP Client.

Provides a unified interface to replace yfinance with Alpha Vantage data:
  * GLOBAL_QUOTE           → replaces yf.Ticker().fast_info / .info (live price)
  * TIME_SERIES_DAILY_ADJUSTED → replaces yf.download()
  * COMPANY_OVERVIEW       → replaces yf.Ticker().info (fundamentals / KPIs)
  * INCOME_STATEMENT       → replaces yf.Ticker().financials
  * BALANCE_SHEET          → replaces yf.Ticker().balance_sheet
  * CASH_FLOW              → replaces yf.Ticker().cashflow
  * NEWS_SENTIMENT         → new NLP / sentiment feature
  * SYMBOL_SEARCH          → replaces yf.Search()
"""
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from app.config.alpha_vantage_config import AlphaVantageConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Symbol helpers
# ---------------------------------------------------------------------------

def _av_symbol(yf_symbol: str) -> str:
    """
    Convert a yfinance-style symbol to Alpha Vantage format.

    yfinance uses  ``RELIANCE.BO``  (BSE)  and  ``RELIANCE.NS``  (NSE).
    Alpha Vantage accepts the bare ticker for Indian exchanges when using
    the SYMBOL_SEARCH endpoint, and some endpoints accept ``BSE:RELIANCE``
    notation.  For maximum compatibility we strip the exchange suffix and
    pass the bare ticker; callers that need exchange context can use the
    ``exchange`` parameter exposed on search results.
    """
    return yf_symbol.replace('.BO', '').replace('.NS', '').upper()


def _parse_float(value: Any, default: float = 0.0) -> float:
    """Safely parse a value to float."""
    if value is None or value == 'None' or value == '-':
        return default
    try:
        return float(str(value).replace(',', ''))
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# In-process cache
# ---------------------------------------------------------------------------

class _Cache:
    """Thread-safe TTL cache keyed by (function, symbol)."""

    def __init__(self):
        self._store: Dict[str, tuple] = {}  # key → (expiry_ts, data)
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry and datetime.now().timestamp() < entry[0]:
                return entry[1]
            return None

    def set(self, key: str, data: Any, ttl: int):
        with self._lock:
            expiry = datetime.now().timestamp() + ttl
            self._store[key] = (expiry, data)

    def invalidate(self, key: str):
        with self._lock:
            self._store.pop(key, None)


_cache = _Cache()


# ---------------------------------------------------------------------------
# Rate limiter (simple token-bucket for the free-tier 5 req/min limit)
# ---------------------------------------------------------------------------

class _RateLimiter:
    def __init__(self, calls_per_minute: int = 5):
        self._min_interval = 60.0 / calls_per_minute
        self._last_call_ts = 0.0
        self._lock = threading.Lock()

    def acquire(self):
        with self._lock:
            elapsed = time.time() - self._last_call_ts
            wait = self._min_interval - elapsed
            if wait > 0:
                time.sleep(wait)
            self._last_call_ts = time.time()


_rate_limiter = _RateLimiter(AlphaVantageConfig.RATE_LIMIT_PER_MINUTE)


# ---------------------------------------------------------------------------
# Core HTTP helper
# ---------------------------------------------------------------------------

def _call_api(params: Dict[str, str], max_retries: int = AlphaVantageConfig.MAX_RETRIES) -> Dict:
    """
    Execute a single Alpha Vantage API call with rate limiting and retries.

    Returns the parsed JSON dict, or raises on persistent failure.
    """
    params['apikey'] = AlphaVantageConfig.API_KEY

    last_exc: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            _rate_limiter.acquire()
            resp = requests.get(
                AlphaVantageConfig.BASE_URL,
                params=params,
                timeout=AlphaVantageConfig.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            # Alpha Vantage signals API-level errors via these keys
            if 'Error Message' in data:
                raise ValueError(f"Alpha Vantage API error: {data['Error Message']}")
            if 'Note' in data:
                # Rate-limit note — back off and retry
                logger.warning("Alpha Vantage rate-limit note: %s", data['Note'])
                if attempt < max_retries:
                    time.sleep(AlphaVantageConfig.RETRY_DELAY)
                continue
            if 'Information' in data:
                # Usually means demo key or daily quota hit
                logger.warning("Alpha Vantage info message: %s", data['Information'])
                return {}

            return data

        except requests.RequestException as exc:
            last_exc = exc
            logger.warning("Alpha Vantage HTTP error (attempt %d/%d): %s", attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(AlphaVantageConfig.RETRY_DELAY)

        except ValueError as exc:
            raise exc  # API error — no point retrying

    if last_exc:
        raise last_exc
    return {}


# ---------------------------------------------------------------------------
# Public API functions
# ---------------------------------------------------------------------------

def get_global_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a real-time (delayed) stock quote via GLOBAL_QUOTE.

    Returns a dict in the same BSE-compatible format used by
    ``yfinance_utils.get_quote_with_retry``, so it can be used as a
    drop-in replacement.

    Tool: GLOBAL_QUOTE
    Confidence Score: 85% (real-time delayed ~15 min)
    """
    av_sym = _av_symbol(symbol)
    cache_key = f"global_quote:{av_sym}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        data = _call_api({'function': 'GLOBAL_QUOTE', 'symbol': av_sym})
        gq = data.get('Global Quote', {})
        if not gq:
            logger.warning("No GLOBAL_QUOTE data for %s", av_sym)
            return None

        price = _parse_float(gq.get('05. price'))
        prev_close = _parse_float(gq.get('08. previous close'))
        change = _parse_float(gq.get('09. change'))
        change_pct_str = str(gq.get('10. change percent', '0%')).replace('%', '')
        change_pct = _parse_float(change_pct_str)
        high = _parse_float(gq.get('03. high'))
        low = _parse_float(gq.get('04. low'))
        volume = _parse_float(gq.get('06. volume'))
        open_price = _parse_float(gq.get('02. open'))

        # Build BSE-compatible dict so existing code needs zero changes
        quote = {
            'companyName': av_sym,
            'securityID': symbol.replace('.BO', '').replace('.NS', ''),
            'scripCode': av_sym,
            'currentValue': price,
            'change': change,
            'pChange': change_pct,
            'dayHigh': high,
            'dayLow': low,
            'previousClose': prev_close,
            'previousOpen': open_price,
            '52weekHigh': 0,
            '52weekLow': 0,
            'faceValue': 0,
            'group': '',
            'industry': '',
            'marketCapFull': '',
            'marketCapFreeFloat': '',
            'totalTradedQuantity': volume,
            'totalTradedValue': '',
            'weightedAvgPrice': price,
            '2WeekAvgQuantity': '',
            'updatedOn': pd.Timestamp.now().strftime('%d %b %y'),
            'buy': {},
            'sell': {},
            # Alpha Vantage extras
            '_source': 'alpha_vantage',
            '_latest_trading_day': gq.get('07. latest trading day', ''),
        }

        _cache.set(cache_key, quote, AlphaVantageConfig.QUOTE_CACHE_TTL)
        return quote

    except Exception as exc:
        logger.error("get_global_quote failed for %s: %s", symbol, exc)
        return None


def get_time_series_daily(
    symbol: str,
    outputsize: str = AlphaVantageConfig.DEFAULT_OUTPUTSIZE,
    adjusted: bool = True,
) -> Optional[pd.DataFrame]:
    """
    Fetch daily OHLCV data via TIME_SERIES_DAILY_ADJUSTED (or TIME_SERIES_DAILY).

    Returns a pandas DataFrame with columns [Open, High, Low, Close, Volume]
    indexed by date — same format as ``yf.download()``.

    Tool: TIME_SERIES_DAILY_ADJUSTED
    Confidence Score: 95% (end-of-day adjusted close)
    """
    av_sym = _av_symbol(symbol)
    cache_key = f"daily_{'adj' if adjusted else 'raw'}:{av_sym}:{outputsize}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        func = 'TIME_SERIES_DAILY_ADJUSTED' if adjusted else 'TIME_SERIES_DAILY'
        data = _call_api({'function': func, 'symbol': av_sym, 'outputsize': outputsize})

        ts_key = 'Time Series (Daily)'
        if ts_key not in data:
            logger.warning("No daily time series data for %s", av_sym)
            return None

        ts = data[ts_key]
        records = []
        close_col = '5. adjusted close' if adjusted else '4. close'
        for date_str, values in ts.items():
            records.append({
                'Date': pd.to_datetime(date_str),
                'Open': _parse_float(values.get('1. open')),
                'High': _parse_float(values.get('2. high')),
                'Low': _parse_float(values.get('3. low')),
                'Close': _parse_float(values.get(close_col, values.get('4. close'))),
                'Volume': _parse_float(values.get('6. volume', values.get('5. volume'))),
            })

        if not records:
            return None

        df = pd.DataFrame(records).set_index('Date').sort_index()
        _cache.set(cache_key, df, AlphaVantageConfig.DAILY_CACHE_TTL)
        return df

    except Exception as exc:
        logger.error("get_time_series_daily failed for %s: %s", symbol, exc)
        return None


def get_company_overview(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch fundamental data via COMPANY_OVERVIEW.

    Replaces ``yf.Ticker().info`` for KPIs, sector classification, and
    market-cap bucketing.

    Tool: COMPANY_OVERVIEW
    Confidence Score: 90% (sourced from SEC filings / exchange data)
    """
    av_sym = _av_symbol(symbol)
    cache_key = f"overview:{av_sym}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        data = _call_api({'function': 'OVERVIEW', 'symbol': av_sym})
        if not data or 'Symbol' not in data:
            logger.warning("No OVERVIEW data for %s", av_sym)
            return None

        _cache.set(cache_key, data, AlphaVantageConfig.FUNDAMENTAL_CACHE_TTL)
        return data

    except Exception as exc:
        logger.error("get_company_overview failed for %s: %s", symbol, exc)
        return None


def get_income_statement(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch annual/quarterly income statement via INCOME_STATEMENT.

    Replaces ``yf.Ticker().financials``.

    Tool: INCOME_STATEMENT
    Confidence Score: 90%
    """
    av_sym = _av_symbol(symbol)
    cache_key = f"income:{av_sym}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        data = _call_api({'function': 'INCOME_STATEMENT', 'symbol': av_sym})
        if not data or 'annualReports' not in data:
            return None
        _cache.set(cache_key, data, AlphaVantageConfig.FUNDAMENTAL_CACHE_TTL)
        return data

    except Exception as exc:
        logger.error("get_income_statement failed for %s: %s", symbol, exc)
        return None


def get_balance_sheet(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch annual/quarterly balance sheet via BALANCE_SHEET.

    Replaces ``yf.Ticker().balance_sheet``.

    Tool: BALANCE_SHEET
    Confidence Score: 90%
    """
    av_sym = _av_symbol(symbol)
    cache_key = f"balance:{av_sym}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        data = _call_api({'function': 'BALANCE_SHEET', 'symbol': av_sym})
        if not data or 'annualReports' not in data:
            return None
        _cache.set(cache_key, data, AlphaVantageConfig.FUNDAMENTAL_CACHE_TTL)
        return data

    except Exception as exc:
        logger.error("get_balance_sheet failed for %s: %s", symbol, exc)
        return None


def get_cash_flow(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch annual/quarterly cash-flow statement via CASH_FLOW.

    Replaces ``yf.Ticker().cashflow``.

    Tool: CASH_FLOW
    Confidence Score: 90%
    """
    av_sym = _av_symbol(symbol)
    cache_key = f"cashflow:{av_sym}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        data = _call_api({'function': 'CASH_FLOW', 'symbol': av_sym})
        if not data or 'annualReports' not in data:
            return None
        _cache.set(cache_key, data, AlphaVantageConfig.FUNDAMENTAL_CACHE_TTL)
        return data

    except Exception as exc:
        logger.error("get_cash_flow failed for %s: %s", symbol, exc)
        return None


def get_news_sentiment(
    symbol: str,
    topics: Optional[str] = None,
    limit: int = 50,
) -> Optional[Dict[str, Any]]:
    """
    Fetch news articles with sentiment scores via NEWS_SENTIMENT.

    Tool: NEWS_SENTIMENT
    Confidence Score: 80% (ML-derived sentiment from aggregated news feeds)

    Returns a dict with keys:
      * ``feed``        – list of article dicts (title, url, time_published,
                          overall_sentiment_score, overall_sentiment_label,
                          ticker_sentiment list)
      * ``sentiment_summary`` – aggregated stats (bullish_count, bearish_count, etc.)
    """
    av_sym = _av_symbol(symbol)
    cache_key = f"news_sentiment:{av_sym}:{topics}:{limit}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        params: Dict[str, str] = {
            'function': 'NEWS_SENTIMENT',
            'tickers': av_sym,
            'limit': str(limit),
            'sort': 'LATEST',
        }
        if topics:
            params['topics'] = topics

        data = _call_api(params)
        if not data or 'feed' not in data:
            logger.warning("No NEWS_SENTIMENT data for %s", av_sym)
            return None

        feed = data.get('feed', [])

        # Build sentiment summary
        scores = []
        labels: Dict[str, int] = {}
        for article in feed:
            score = _parse_float(article.get('overall_sentiment_score'), default=None)
            if score is not None:
                scores.append(score)
            label = article.get('overall_sentiment_label', 'Neutral')
            labels[label] = labels.get(label, 0) + 1

        summary = {
            'total_articles': len(feed),
            'average_sentiment_score': round(sum(scores) / len(scores), 4) if scores else 0.0,
            'sentiment_label_distribution': labels,
            'bullish_count': labels.get('Bullish', 0) + labels.get('Somewhat-Bullish', 0),
            'bearish_count': labels.get('Bearish', 0) + labels.get('Somewhat-Bearish', 0),
            'neutral_count': labels.get('Neutral', 0),
        }

        result = {'feed': feed, 'sentiment_summary': summary, 'symbol': av_sym}
        _cache.set(cache_key, result, AlphaVantageConfig.SENTIMENT_CACHE_TTL)
        return result

    except Exception as exc:
        logger.error("get_news_sentiment failed for %s: %s", symbol, exc)
        return None


def search_symbol(
    keywords: str,
    indian_only: bool = True,
) -> List[Dict[str, Any]]:
    """
    Search for ticker symbols via SYMBOL_SEARCH.

    Replaces ``yf.Search()``.

    Returns a list of dicts with keys:
      symbol, name, type, region, currency, matchScore.
    """
    cache_key = f"search:{keywords}:{indian_only}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        data = _call_api({'function': 'SYMBOL_SEARCH', 'keywords': keywords})
        matches = data.get('bestMatches', [])

        results: List[Dict[str, Any]] = []
        for item in matches:
            region = item.get('4. region', '')
            # Filter to Indian exchanges if requested
            if indian_only and region not in ('India',):
                continue
            results.append({
                'symbol': item.get('1. symbol', ''),
                'name': item.get('2. name', ''),
                'type': item.get('3. type', ''),
                'region': region,
                'currency': item.get('8. currency', ''),
                'exchange': item.get('4. region', ''),
                'matchScore': _parse_float(item.get('9. matchScore', '0')),
            })

        _cache.set(cache_key, results, AlphaVantageConfig.DAILY_CACHE_TTL)
        return results

    except Exception as exc:
        logger.error("search_symbol failed for '%s': %s", keywords, exc)
        return []


def get_earnings_calendar(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch upcoming earnings calendar via EARNINGS_CALENDAR.

    Tool: EARNINGS_CALENDAR
    Confidence Score: 85%
    """
    av_sym = _av_symbol(symbol)
    cache_key = f"earnings:{av_sym}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        data = _call_api({'function': 'EARNINGS_CALENDAR', 'symbol': av_sym, 'horizon': '3month'})
        _cache.set(cache_key, data, AlphaVantageConfig.FUNDAMENTAL_CACHE_TTL)
        return data

    except Exception as exc:
        logger.error("get_earnings_calendar failed for %s: %s", symbol, exc)
        return None
