"""
Alpha Vantage stock data utilities.

Provides functions to fetch stock quotes and search for companies using
the Alpha Vantage API (https://www.alphavantage.co/).

Set the ALPHA_VANTAGE_API_KEY environment variable to enable this module.
"""
import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests

ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
_REQUEST_TIMEOUT = 10  # seconds


def _get_api_key() -> str:
    """Return the Alpha Vantage API key from environment variables."""
    return os.getenv("ALPHA_VANTAGE_API_KEY", "")


def _yfinance_symbol_to_av(symbol: str) -> str:
    """
    Convert a yfinance-style symbol to Alpha Vantage format.

    Examples:
        RELIANCE.BO  -> RELIANCE.BSE
        RELIANCE.NS  -> RELIANCE.NSE
        IBM          -> IBM  (unchanged)
    """
    if symbol.endswith(".BO"):
        return symbol[:-3] + ".BSE"
    if symbol.endswith(".NS"):
        return symbol[:-3] + ".NSE"
    return symbol


def get_quote(symbol: str, max_retries: int = 3, delay: int = 1) -> Optional[Dict[str, Any]]:
    """
    Fetch a stock quote from the Alpha Vantage GLOBAL_QUOTE endpoint.

    Args:
        symbol: Stock symbol in yfinance format (e.g. ``RELIANCE.BO``).
        max_retries: Number of retry attempts on transient errors.
        delay: Seconds to wait between retries.

    Returns:
        Dictionary in BSE-compatible format (same schema as
        :func:`app.utils.yfinance_utils.get_quote_with_retry`), or ``None``
        when the quote cannot be retrieved.
    """
    api_key = _get_api_key()
    if not api_key:
        logging.debug("Alpha Vantage API key not configured; skipping AV quote fetch.")
        return None

    av_symbol = _yfinance_symbol_to_av(symbol)
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": av_symbol,
        "apikey": api_key,
    }

    last_exception: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            # Alpha Vantage returns a "Note" key when the rate limit is hit
            if "Note" in data:
                logging.warning("Alpha Vantage rate limit reached: %s", data["Note"])
                return None

            # Alpha Vantage returns an "Information" key on API key issues
            if "Information" in data:
                logging.warning("Alpha Vantage API information: %s", data["Information"])
                return None

            gq = data.get("Global Quote", {})
            if not gq or not gq.get("05. price"):
                logging.warning(
                    "Alpha Vantage returned empty Global Quote for %s (attempt %d)",
                    av_symbol,
                    attempt,
                )
                if attempt < max_retries:
                    time.sleep(delay)
                    continue
                return None

            price = float(gq.get("05. price", 0))
            prev_close = float(gq.get("08. previous close", 0))
            change = float(gq.get("09. change", 0))
            change_pct_raw = gq.get("10. change percent", "0%").replace("%", "")
            change_pct = float(change_pct_raw) if change_pct_raw else 0.0

            return {
                "companyName": gq.get("01. symbol", symbol),
                "securityID": (
                    symbol.replace(".BO", "").replace(".NS", "")
                           .replace(".BSE", "").replace(".NSE", "")
                ),
                "scripCode": gq.get("01. symbol", symbol),
                "currentValue": price,
                "change": change,
                "pChange": change_pct,
                "dayHigh": float(gq.get("03. high", 0)),
                "dayLow": float(gq.get("04. low", 0)),
                "previousClose": prev_close,
                "previousOpen": float(gq.get("02. open", 0)),
                "52weekHigh": 0,
                "52weekLow": 0,
                "faceValue": 0,
                "group": "",
                "industry": "",
                "marketCapFull": "",
                "marketCapFreeFloat": "",
                "totalTradedQuantity": gq.get("06. volume", ""),
                "totalTradedValue": "",
                "weightedAvgPrice": price,
                "2WeekAvgQuantity": "",
                "updatedOn": gq.get("07. latest trading day", ""),
                "buy": {},
                "sell": {},
            }

        except (requests.RequestException, ValueError, KeyError) as exc:
            last_exception = exc
            logging.warning("Alpha Vantage quote attempt %d failed for %s: %s", attempt, av_symbol, exc)
            if attempt < max_retries:
                time.sleep(delay)

    logging.error("All %d Alpha Vantage quote attempts failed for %s", max_retries, av_symbol)
    if last_exception:
        logging.debug("Last exception: %s", last_exception)
    return None


def search_companies(
    keywords: str,
    max_results: int = 10,
    indian_only: bool = True,
    max_retries: int = 3,
    delay: int = 1,
) -> List[Dict[str, Any]]:
    """
    Search for companies using the Alpha Vantage SYMBOL_SEARCH endpoint.

    Args:
        keywords: Company name or ticker keywords to search for.
        max_results: Maximum number of results to return.
        indian_only: When ``True``, only return results from Indian exchanges.
        max_retries: Number of retry attempts on transient errors.
        delay: Seconds to wait between retries.

    Returns:
        List of dicts with keys ``symbol``, ``name``, ``exchange``, ``type``,
        ``industry``, ``sector`` (same schema as
        :func:`app.utils.yfinance_utils.search_companies_by_name`).
    """
    api_key = _get_api_key()
    if not api_key:
        logging.debug("Alpha Vantage API key not configured; skipping AV company search.")
        return []

    params = {
        "function": "SYMBOL_SEARCH",
        "keywords": keywords,
        "apikey": api_key,
    }
    indian_exchanges = {"BSE", "NSE"}

    last_exception: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if "Note" in data:
                logging.warning("Alpha Vantage rate limit reached: %s", data["Note"])
                return []

            if "Information" in data:
                logging.warning("Alpha Vantage API information: %s", data["Information"])
                return []

            best_matches = data.get("bestMatches", [])
            results: List[Dict[str, Any]] = []
            for item in best_matches:
                symbol = item.get("1. symbol", "")
                name = item.get("2. name", symbol)
                exchange = item.get("4. region", "")
                match_type = item.get("3. type", "")

                # Alpha Vantage uses region names like "United States", "India" etc.
                # Filter to Indian stocks when requested; use symbol suffix for accuracy.
                symbol_is_indian = symbol.endswith(".BSE") or symbol.endswith(".NSE")
                region_is_india = "india" in exchange.lower()
                if indian_only and not symbol_is_indian and not region_is_india:
                    continue

                # Normalise exchange label so downstream consumers see BSE/NSE
                if symbol.endswith(".BSE"):
                    exchange = "BSE"
                elif symbol.endswith(".NSE"):
                    exchange = "NSE"
                elif region_is_india:
                    exchange = "India"

                results.append(
                    {
                        "symbol": symbol,
                        "name": name,
                        "exchange": exchange,
                        "type": match_type,
                        "industry": "",
                        "sector": "",
                    }
                )

                if len(results) >= max_results:
                    break

            logging.info(
                "Alpha Vantage search returned %d results for '%s'", len(results), keywords
            )
            return results

        except (requests.RequestException, ValueError, KeyError) as exc:
            last_exception = exc
            logging.warning(
                "Alpha Vantage search attempt %d failed for '%s': %s", attempt, keywords, exc
            )
            if attempt < max_retries:
                time.sleep(delay)

    logging.error(
        "All %d Alpha Vantage search attempts failed for '%s'", max_retries, keywords
    )
    if last_exception:
        logging.debug("Last exception: %s", last_exception)
    return []
