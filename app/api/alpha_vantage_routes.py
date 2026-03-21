"""
Alpha Vantage MCP Routes.

Provides REST endpoints that expose Alpha Vantage data to the frontend:
  GET /api/av/quote/<symbol>        – Real-time quote (GLOBAL_QUOTE)
  GET /api/av/historical/<symbol>   – Daily OHLCV (TIME_SERIES_DAILY_ADJUSTED)
  GET /api/av/fundamentals/<symbol> – KPIs + financial statements
  GET /api/av/sentiment/<symbol>    – News sentiment (NEWS_SENTIMENT)
  GET /api/av/search                – Symbol search (SYMBOL_SEARCH)
  GET /api/av/visualize/<symbol>    – Embedded chart images

Decision Transparency
---------------------
Each response includes a ``_meta`` block documenting:
  * tool_used       – Alpha Vantage function name
  * data_source     – 'alpha_vantage' | 'yfinance_fallback'
  * confidence_pct  – Confidence score (0-100)
  * timestamp       – ISO-8601 generation time
"""
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import login_required

from app.config.alpha_vantage_config import AlphaVantageConfig

logger = logging.getLogger(__name__)

alpha_vantage_bp = Blueprint('alpha_vantage', __name__, url_prefix='/api/av')


def _meta(tool: str, source: str, confidence: int) -> dict:
    return {
        '_meta': {
            'tool_used': tool,
            'data_source': source,
            'confidence_pct': confidence,
            'timestamp': datetime.now().isoformat(),
        }
    }


# ---------------------------------------------------------------------------
# 1. Real-time Quote
# ---------------------------------------------------------------------------

@alpha_vantage_bp.route('/quote/<symbol>', methods=['GET'])
@login_required
def get_quote(symbol: str):
    """
    Fetch real-time (delayed) stock quote.

    Tool: GLOBAL_QUOTE  |  Confidence: 85%

    Returns BSE-compatible quote dict plus ``_meta`` block.
    """
    try:
        from app.utils.alpha_vantage_client import get_global_quote
        quote = get_global_quote(symbol)

        if quote:
            return jsonify({
                'success': True,
                'quote': quote,
                **_meta('GLOBAL_QUOTE', 'alpha_vantage', 85),
            })

        # Fallback to yfinance
        from app.utils.yfinance_utils import get_quote_with_retry
        quote = get_quote_with_retry(symbol)
        if quote:
            return jsonify({
                'success': True,
                'quote': quote,
                **_meta('yfinance_ticker', 'yfinance_fallback', 70),
            })

        return jsonify({'success': False, 'error': f'No quote data for {symbol}'}), 404

    except Exception as exc:
        logger.error("Error in get_quote for %s: %s", symbol, exc)
        return jsonify({'success': False, 'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# 2. Historical Daily Series
# ---------------------------------------------------------------------------

@alpha_vantage_bp.route('/historical/<symbol>', methods=['GET'])
@login_required
def get_historical(symbol: str):
    """
    Fetch daily OHLCV data.

    Tool: TIME_SERIES_DAILY_ADJUSTED  |  Confidence: 95%

    Query params:
      outputsize: 'compact' (default, 100 days) | 'full' (20+ years)
      limit:      max rows to return (default 100)
    """
    outputsize = request.args.get('outputsize', 'compact')
    limit = int(request.args.get('limit', 100))

    try:
        from app.utils.alpha_vantage_client import get_time_series_daily
        df = get_time_series_daily(symbol, outputsize=outputsize)

        if df is not None and not df.empty:
            df_tail = df.tail(limit)
            records = [
                {
                    'date': str(idx.date()),
                    'open': row['Open'],
                    'high': row['High'],
                    'low': row['Low'],
                    'close': row['Close'],
                    'volume': int(row['Volume']),
                }
                for idx, row in df_tail.iterrows()
            ]
            return jsonify({
                'success': True,
                'symbol': symbol,
                'data': records,
                'total_rows': len(df),
                'returned_rows': len(records),
                **_meta('TIME_SERIES_DAILY_ADJUSTED', 'alpha_vantage', 95),
            })

        return jsonify({'success': False, 'error': f'No historical data for {symbol}'}), 404

    except Exception as exc:
        logger.error("Error in get_historical for %s: %s", symbol, exc)
        return jsonify({'success': False, 'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# 3. Fundamentals (COMPANY_OVERVIEW + financial statements)
# ---------------------------------------------------------------------------

@alpha_vantage_bp.route('/fundamentals/<symbol>', methods=['GET'])
@login_required
def get_fundamentals(symbol: str):
    """
    Fetch company overview and financial statements.

    Tools used:
      * COMPANY_OVERVIEW   → KPIs, sector, market cap   (Confidence: 90%)
      * INCOME_STATEMENT   → Revenue, EPS trends         (Confidence: 90%)
      * BALANCE_SHEET      → Assets, liabilities         (Confidence: 90%)
      * CASH_FLOW          → Operating / free cash flow  (Confidence: 90%)

    Returns a comprehensive fundamentals dict plus ``_meta`` block.
    """
    include = set(request.args.get('include', 'overview,income,balance,cashflow').split(','))

    try:
        from app.utils.alpha_vantage_client import (
            get_company_overview,
            get_income_statement,
            get_balance_sheet,
            get_cash_flow,
        )

        result: dict = {'success': True, 'symbol': symbol}
        tools_used = []

        if 'overview' in include:
            overview = get_company_overview(symbol)
            if overview:
                result['overview'] = overview
                tools_used.append('COMPANY_OVERVIEW')

        if 'income' in include:
            income = get_income_statement(symbol)
            if income:
                result['income_statement'] = {
                    'annual': income.get('annualReports', [])[:5],
                    'quarterly': income.get('quarterlyReports', [])[:4],
                }
                tools_used.append('INCOME_STATEMENT')

        if 'balance' in include:
            balance = get_balance_sheet(symbol)
            if balance:
                result['balance_sheet'] = {
                    'annual': balance.get('annualReports', [])[:5],
                    'quarterly': balance.get('quarterlyReports', [])[:4],
                }
                tools_used.append('BALANCE_SHEET')

        if 'cashflow' in include:
            cashflow = get_cash_flow(symbol)
            if cashflow:
                result['cash_flow'] = {
                    'annual': cashflow.get('annualReports', [])[:5],
                    'quarterly': cashflow.get('quarterlyReports', [])[:4],
                }
                tools_used.append('CASH_FLOW')

        result.update(_meta('+'.join(tools_used) or 'N/A', 'alpha_vantage', 90))

        if len(result) <= 3:  # only success + symbol + _meta
            return jsonify({'success': False, 'error': f'No fundamental data for {symbol}'}), 404

        return jsonify(result)

    except Exception as exc:
        logger.error("Error in get_fundamentals for %s: %s", symbol, exc)
        return jsonify({'success': False, 'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# 4. News Sentiment
# ---------------------------------------------------------------------------

@alpha_vantage_bp.route('/sentiment/<symbol>', methods=['GET'])
@login_required
def get_sentiment(symbol: str):
    """
    Fetch news articles and ML-derived sentiment scores.

    Tool: NEWS_SENTIMENT  |  Confidence: 80%

    Query params:
      topics: comma-separated topic filter (optional)
      limit:  max articles (default 50)
    """
    topics = request.args.get('topics')
    limit = int(request.args.get('limit', 50))

    try:
        from app.utils.alpha_vantage_client import get_news_sentiment
        data = get_news_sentiment(symbol, topics=topics, limit=limit)

        if data:
            return jsonify({
                'success': True,
                'symbol': symbol,
                **data,
                **_meta('NEWS_SENTIMENT', 'alpha_vantage', 80),
            })

        return jsonify({'success': False, 'error': f'No sentiment data for {symbol}'}), 404

    except Exception as exc:
        logger.error("Error in get_sentiment for %s: %s", symbol, exc)
        return jsonify({'success': False, 'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# 5. Symbol Search
# ---------------------------------------------------------------------------

@alpha_vantage_bp.route('/search', methods=['GET'])
@login_required
def search_symbol():
    """
    Search for company / ticker symbols.

    Tool: SYMBOL_SEARCH  |  Confidence: 88%

    Query params:
      q:            search keywords (required)
      indian_only:  'true' | 'false' (default true)
    """
    keywords = request.args.get('q', '').strip()
    if not keywords:
        return jsonify({'success': False, 'error': 'Missing query parameter q'}), 400

    indian_only = request.args.get('indian_only', 'true').lower() != 'false'

    try:
        from app.utils.alpha_vantage_client import search_symbol as av_search
        results = av_search(keywords, indian_only=indian_only)

        return jsonify({
            'success': True,
            'query': keywords,
            'results': results,
            **_meta('SYMBOL_SEARCH', 'alpha_vantage', 88),
        })

    except Exception as exc:
        logger.error("Error in search_symbol for '%s': %s", keywords, exc)
        return jsonify({'success': False, 'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# 6. Visualizations
# ---------------------------------------------------------------------------

@alpha_vantage_bp.route('/visualize/<symbol>', methods=['GET'])
@login_required
def visualize(symbol: str):
    """
    Generate and return embedded chart images as base64 PNG strings.

    Chart types (``type`` query param):
      * price      – OHLCV price history with SMA overlays  (default)
      * kpi        – KPI dashboard (fundamental metrics)
      * sentiment  – News sentiment distribution & time-series
      * forecast   – ML price forecast overlay

    Returns JSON with ``chart_b64`` key (base64 PNG data-URI).
    """
    chart_type = request.args.get('type', 'price')

    try:
        from app.utils.alpha_vantage_client import (
            get_time_series_daily,
            get_company_overview,
            get_news_sentiment,
        )
        from app.utils.visualization_utils import (
            plot_price_history,
            plot_kpi_dashboard,
            plot_sentiment_analysis,
            plot_forecast,
        )

        chart_b64 = None

        if chart_type == 'price':
            df = get_time_series_daily(symbol, outputsize='compact')
            if df is not None and not df.empty:
                chart_b64 = plot_price_history(df, symbol)
            tools = 'TIME_SERIES_DAILY_ADJUSTED'

        elif chart_type == 'kpi':
            overview = get_company_overview(symbol)
            if overview:
                chart_b64 = plot_kpi_dashboard(overview, symbol)
            tools = 'COMPANY_OVERVIEW'

        elif chart_type == 'sentiment':
            data = get_news_sentiment(symbol)
            if data:
                chart_b64 = plot_sentiment_analysis(data, symbol)
            tools = 'NEWS_SENTIMENT'

        elif chart_type == 'forecast':
            df = get_time_series_daily(symbol, outputsize='compact')
            predicted_price = float(request.args.get('predicted_price', 0))
            confidence = float(request.args.get('confidence', 0.5))
            if df is not None and not df.empty and predicted_price:
                chart_b64 = plot_forecast(df, predicted_price, symbol, confidence)
            tools = 'TIME_SERIES_DAILY_ADJUSTED'

        else:
            return jsonify({'success': False, 'error': f'Unknown chart type: {chart_type}'}), 400

        if not chart_b64:
            return jsonify({
                'success': False,
                'error': f'Could not generate {chart_type} chart for {symbol} — no data available',
            }), 404

        return jsonify({
            'success': True,
            'symbol': symbol,
            'chart_type': chart_type,
            'chart_b64': chart_b64,
            **_meta(tools, 'alpha_vantage', 90),
        })

    except Exception as exc:
        logger.error("Error in visualize for %s (%s): %s", symbol, chart_type, exc)
        return jsonify({'success': False, 'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# 7. Health / configuration check
# ---------------------------------------------------------------------------

@alpha_vantage_bp.route('/status', methods=['GET'])
@login_required
def av_status():
    """Return Alpha Vantage integration status (is API key configured?)."""
    return jsonify({
        'success': True,
        'configured': AlphaVantageConfig.is_configured(),
        'api_key_present': AlphaVantageConfig.API_KEY not in ('demo', '', None),
        'base_url': AlphaVantageConfig.BASE_URL,
        'rate_limit_per_minute': AlphaVantageConfig.RATE_LIMIT_PER_MINUTE,
        'tools_available': [
            'GLOBAL_QUOTE',
            'TIME_SERIES_DAILY_ADJUSTED',
            'COMPANY_OVERVIEW',
            'INCOME_STATEMENT',
            'BALANCE_SHEET',
            'CASH_FLOW',
            'NEWS_SENTIMENT',
            'SYMBOL_SEARCH',
            'EARNINGS_CALENDAR',
        ],
    })
