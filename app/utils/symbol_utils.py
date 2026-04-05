"""
Symbol normalization utilities - handles ticker normalization,
exchange suffix management, and input validation for market symbols.
"""
import re
from typing import Optional, Tuple


# Exchange suffix mappings
EXCHANGE_SUFFIXES = {
    'NSE': '.NS',
    'BSE': '.BO',
    'NYSE': '',
    'NASDAQ': '',
}

# Common exchange suffixes from Yahoo Finance
KNOWN_SUFFIXES = {'.NS', '.BO', '.L', '.HK', '.T', '.AX', '.TO', '.SI', '.KS'}


def normalize_symbol(symbol: str, default_exchange: str = 'NSE') -> str:
    """
    Normalize a stock symbol to Yahoo Finance format.

    Examples:
        normalize_symbol('RELIANCE') -> 'RELIANCE.NS'
        normalize_symbol('RELIANCE.NS') -> 'RELIANCE.NS'
        normalize_symbol('TCS.BO') -> 'TCS.BO'
        normalize_symbol('AAPL', 'NYSE') -> 'AAPL'
    """
    if not symbol:
        return symbol

    symbol = symbol.strip().upper()

    # Already has a known suffix
    for suffix in KNOWN_SUFFIXES:
        if symbol.endswith(suffix):
            return symbol

    # Apply default exchange suffix
    suffix = EXCHANGE_SUFFIXES.get(default_exchange.upper(), '')
    return symbol + suffix


def strip_exchange_suffix(symbol: str) -> str:
    """Remove exchange suffix from a symbol."""
    if not symbol:
        return symbol
    for suffix in KNOWN_SUFFIXES:
        if symbol.endswith(suffix):
            return symbol[:-len(suffix)]
    return symbol


def get_exchange(symbol: str) -> str:
    """Detect the exchange from a symbol's suffix."""
    if not symbol:
        return 'UNKNOWN'
    symbol = symbol.upper()
    if symbol.endswith('.NS'):
        return 'NSE'
    if symbol.endswith('.BO'):
        return 'BSE'
    if symbol.endswith('.L'):
        return 'LSE'
    if symbol.endswith('.HK'):
        return 'HKEX'
    if symbol.endswith('.T'):
        return 'TSE'
    # No suffix - assume US market
    if not any(symbol.endswith(s) for s in KNOWN_SUFFIXES):
        return 'US'
    return 'UNKNOWN'


def parse_symbol_input(raw_input: str, default_exchange: str = 'NSE') -> Tuple[str, str]:
    """
    Parse user input into (normalized_symbol, base_symbol).
    Handles formats like: "RELIANCE", "RELIANCE.NS", "NSE:RELIANCE"
    """
    if not raw_input:
        return ('', '')

    raw = raw_input.strip().upper()

    # Handle "EXCHANGE:SYMBOL" format
    if ':' in raw:
        parts = raw.split(':', 1)
        exchange = parts[0].strip()
        base = parts[1].strip()
        if exchange in EXCHANGE_SUFFIXES:
            return (base + EXCHANGE_SUFFIXES[exchange], base)
        return (base, base)

    # Handle "SYMBOL.SUFFIX" format
    base = strip_exchange_suffix(raw)
    normalized = normalize_symbol(raw, default_exchange)

    return (normalized, base)


def validate_symbol(symbol: str) -> bool:
    """
    Validate that a symbol looks like a valid stock ticker.
    Allows alphanumeric, hyphens, dots, and underscores.
    """
    if not symbol:
        return False
    # Strip suffix for validation
    base = strip_exchange_suffix(symbol)
    if not base:
        return False
    # Ticker should be 1-20 chars, alphanumeric with optional hyphens/underscores
    return bool(re.match(r'^[A-Z0-9][A-Z0-9_\-]{0,19}$', base))


def infer_exchange_from_symbol(symbol: str) -> str:
    """
    Infer the most likely exchange for an Indian stock symbol.
    Most Indian brokers default to NSE.
    """
    base = strip_exchange_suffix(symbol).upper()

    # Check for BSE-specific patterns (numeric scrip codes)
    if base.isdigit():
        return 'BSE'

    # Default to NSE for Indian symbols
    return 'NSE'


def format_display_symbol(symbol: str) -> str:
    """Format a symbol for display (remove suffix for Indian stocks)."""
    base = strip_exchange_suffix(symbol)
    exchange = get_exchange(symbol)
    if exchange in ('NSE', 'BSE'):
        return base
    return symbol
