"""
Market Data Routes (yfinance).

Provides REST endpoints that expose market data to the frontend:
  GET /api/av/quote/<symbol>        – Real-time quote
  GET /api/av/historical/<symbol>   – Daily OHLCV history
  GET /api/av/fundamentals/<symbol> – KPIs + financial statements
  GET /api/av/sentiment/<symbol>    – Recent news articles
  GET /api/av/search                – Symbol search
  GET /api/av/visualize/<symbol>    – Embedded chart images
  GET /api/av/status                – Integration status

Each response includes a ``_meta`` block documenting:
  * tool_used       – yfinance method used
  * data_source     – 'yfinance'
  * confidence_pct  – Confidence score (0-100)
  * timestamp       – ISO-8601 generation time
"""
import logging
from datetime import datetime

import yfinance as yf
import pandas as pd

from flask import Blueprint, jsonify, request
from flask_login import login_required

logger = logging.getLogger(__name__)

alpha_vantage_bp = Blueprint('alpha_vantage', __name__, url_prefix='/api/av')


def _meta(tool: str, confidence: int) -> dict:
    return {
        '_meta': {
            'tool_used': tool,
            'data_source': 'yfinance',
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
    Fetch real-time stock quote via yfinance.

    Tool: yfinance_ticker  |  Confidence: 85%

    Returns BSE-compatible quote dict plus ``_meta`` block.
    """
    try:
        from app.utils.yfinance_utils import get_quote_with_retry
        quote = get_quote_with_retry(symbol)
        if quote:
            return jsonify({
                'success': True,
                'quote': quote,
                **_meta('yfinance_ticker', 85),
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
    Fetch daily OHLCV data via yfinance.

    Tool: yfinance_download  |  Confidence: 95%

    Query params:
      outputsize: 'compact' (default, ~100 days) | 'full' (all available)
      limit:      max rows to return (default 100)
    """
    outputsize = request.args.get('outputsize', 'compact')
    limit = int(request.args.get('limit', 100))
    period = '6mo' if outputsize == 'compact' else 'max'

    try:
        df = yf.download(symbol, period=period, auto_adjust=True, progress=False)

        if df is not None and not df.empty:
            # Flatten multi-level columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df_tail = df.tail(limit)
            records = [
                {
                    'date': str(idx.date()),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
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
                **_meta('yfinance_download', 95),
            })

        return jsonify({'success': False, 'error': f'No historical data for {symbol}'}), 404

    except Exception as exc:
        logger.error("Error in get_historical for %s: %s", symbol, exc)
        return jsonify({'success': False, 'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# 3. Fundamentals (company info + financial statements)
# ---------------------------------------------------------------------------

@alpha_vantage_bp.route('/fundamentals/<symbol>', methods=['GET'])
@login_required
def get_fundamentals(symbol: str):
    """
    Fetch company overview and financial statements via yfinance.

    Tools used:
      * yfinance_info        → KPIs, sector, market cap   (Confidence: 90%)
      * yfinance_financials  → Income statement            (Confidence: 90%)
      * yfinance_balance     → Balance sheet               (Confidence: 90%)
      * yfinance_cashflow    → Cash flow statement         (Confidence: 90%)

    Returns a comprehensive fundamentals dict plus ``_meta`` block.
    """
    include = set(request.args.get('include', 'overview,income,balance,cashflow').split(','))

    try:
        ticker = yf.Ticker(symbol)
        result: dict = {'success': True, 'symbol': symbol}
        tools_used = []

        if 'overview' in include:
            info = ticker.info or {}
            if info:
                result['overview'] = {
                    'Symbol': symbol,
                    'Name': info.get('longName') or info.get('shortName', ''),
                    'Sector': info.get('sector', ''),
                    'Industry': info.get('industry', ''),
                    'MarketCapitalization': info.get('marketCap', ''),
                    'PERatio': info.get('trailingPE', ''),
                    'EPS': info.get('trailingEps', ''),
                    'DividendYield': info.get('dividendYield', ''),
                    'Beta': info.get('beta', ''),
                    '52WeekHigh': info.get('fiftyTwoWeekHigh', ''),
                    '52WeekLow': info.get('fiftyTwoWeekLow', ''),
                    'BookValue': info.get('bookValue', ''),
                    'PriceToBook': info.get('priceToBook', ''),
                    'Description': info.get('longBusinessSummary', ''),
                }
                tools_used.append('yfinance_info')

        if 'income' in include:
            try:
                fin = ticker.financials
                qfin = ticker.quarterly_financials
                if fin is not None and not fin.empty:
                    result['income_statement'] = {
                        'annual': fin.T.reset_index().rename(
                            columns={'index': 'fiscalDateEnding'}
                        ).to_dict(orient='records')[:5],
                        'quarterly': (qfin.T.reset_index().rename(
                            columns={'index': 'fiscalDateEnding'}
                        ).to_dict(orient='records')[:4]) if (qfin is not None and not qfin.empty) else [],
                    }
                    tools_used.append('yfinance_financials')
            except Exception as e:
                logging.debug("yfinance financials fetch failed for %s: %s", symbol, e)

        if 'balance' in include:
            try:
                bs = ticker.balance_sheet
                qbs = ticker.quarterly_balance_sheet
                if bs is not None and not bs.empty:
                    result['balance_sheet'] = {
                        'annual': bs.T.reset_index().rename(
                            columns={'index': 'fiscalDateEnding'}
                        ).to_dict(orient='records')[:5],
                        'quarterly': (qbs.T.reset_index().rename(
                            columns={'index': 'fiscalDateEnding'}
                        ).to_dict(orient='records')[:4]) if (qbs is not None and not qbs.empty) else [],
                    }
                    tools_used.append('yfinance_balance_sheet')
            except Exception as e:
                logging.debug("yfinance balance sheet fetch failed for %s: %s", symbol, e)

        if 'cashflow' in include:
            try:
                cf = ticker.cashflow
                qcf = ticker.quarterly_cashflow
                if cf is not None and not cf.empty:
                    result['cash_flow'] = {
                        'annual': cf.T.reset_index().rename(
                            columns={'index': 'fiscalDateEnding'}
                        ).to_dict(orient='records')[:5],
                        'quarterly': (qcf.T.reset_index().rename(
                            columns={'index': 'fiscalDateEnding'}
                        ).to_dict(orient='records')[:4]) if (qcf is not None and not qcf.empty) else [],
                    }
                    tools_used.append('yfinance_cashflow')
            except Exception as e:
                logging.debug("yfinance cash flow fetch failed for %s: %s", symbol, e)

        result.update(_meta('+'.join(tools_used) or 'N/A', 90))

        if len(result) <= 3:  # only success + symbol + _meta
            return jsonify({'success': False, 'error': f'No fundamental data for {symbol}'}), 404

        return jsonify(result)

    except Exception as exc:
        logger.error("Error in get_fundamentals for %s: %s", symbol, exc)
        return jsonify({'success': False, 'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# 4. News / Sentiment
# ---------------------------------------------------------------------------

@alpha_vantage_bp.route('/sentiment/<symbol>', methods=['GET'])
@login_required
def get_sentiment(symbol: str):
    """
    Fetch recent news articles via yfinance.

    Tool: yfinance_news  |  Confidence: 75%

    Query params:
      limit:  max articles (default 50)
    """
    limit = int(request.args.get('limit', 50))

    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news or []
        feed = news[:limit]

        if not feed:
            return jsonify({'success': False, 'error': f'No news data for {symbol}'}), 404

        articles = [
            {
                'title': item.get('content', {}).get('title', '') or item.get('title', ''),
                'url': (
                    item.get('content', {}).get('canonicalUrl', {}).get('url', '')
                    or item.get('link', '')
                ),
                'time_published': str(
                    item.get('content', {}).get('pubDate', '')
                    or item.get('providerPublishTime', '')
                ),
                'source': (
                    item.get('content', {}).get('provider', {}).get('displayName', '')
                    or item.get('publisher', '')
                ),
                'overall_sentiment_label': 'Neutral',
                'overall_sentiment_score': 0.0,
            }
            for item in feed
        ]

        sentiment_summary = {
            'total_articles': len(articles),
            'average_sentiment_score': 0.0,
            'sentiment_label_distribution': {'Neutral': len(articles)},
            'bullish_count': 0,
            'bearish_count': 0,
            'neutral_count': len(articles),
        }

        return jsonify({
            'success': True,
            'symbol': symbol,
            'feed': articles,
            'sentiment_summary': sentiment_summary,
            **_meta('yfinance_news', 75),
        })

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
    Search for company / ticker symbols via yfinance.

    Tool: yfinance_search  |  Confidence: 88%

    Query params:
      q:            search keywords (required)
      indian_only:  'true' | 'false' (default true)
    """
    keywords = request.args.get('q', '').strip()
    if not keywords:
        return jsonify({'success': False, 'error': 'Missing query parameter q'}), 400

    indian_only = request.args.get('indian_only', 'true').lower() != 'false'

    try:
        from app.utils.yfinance_utils import search_companies_by_name
        results = search_companies_by_name(
            company_name=keywords,
            max_results=20,
            indian_only=indian_only,
        )

        return jsonify({
            'success': True,
            'query': keywords,
            'results': results,
            **_meta('yfinance_search', 88),
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
      * sentiment  – News placeholder chart
      * forecast   – ML price forecast overlay

    Returns JSON with ``chart_b64`` key (base64 PNG data-URI).
    """
    chart_type = request.args.get('type', 'price')

    try:
        from app.utils.visualization_utils import (
            plot_price_history,
            plot_kpi_dashboard,
            plot_sentiment_analysis,
            plot_forecast,
        )

        chart_b64 = None
        tool = 'yfinance_download'

        if chart_type == 'price':
            df = yf.download(symbol, period='6mo', auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df is not None and not df.empty:
                chart_b64 = plot_price_history(df, symbol)

        elif chart_type == 'kpi':
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            if info:
                overview = {
                    'Symbol': symbol,
                    'Name': info.get('longName') or info.get('shortName', ''),
                    'Sector': info.get('sector', ''),
                    'Industry': info.get('industry', ''),
                    'MarketCapitalization': info.get('marketCap', ''),
                    'PERatio': info.get('trailingPE', ''),
                    'EPS': info.get('trailingEps', ''),
                    'DividendYield': info.get('dividendYield', ''),
                    'Beta': info.get('beta', ''),
                    '52WeekHigh': info.get('fiftyTwoWeekHigh', ''),
                    '52WeekLow': info.get('fiftyTwoWeekLow', ''),
                }
                chart_b64 = plot_kpi_dashboard(overview, symbol)
            tool = 'yfinance_info'

        elif chart_type == 'sentiment':
            ticker = yf.Ticker(symbol)
            news = ticker.news or []
            if news:
                sentiment_data = {
                    'feed': [
                        {
                            'title': item.get('content', {}).get('title', '') or item.get('title', ''),
                            'overall_sentiment_label': 'Neutral',
                            'overall_sentiment_score': 0.0,
                        }
                        for item in news[:30]
                    ],
                    'sentiment_summary': {
                        'total_articles': len(news[:30]),
                        'average_sentiment_score': 0.0,
                        'bullish_count': 0,
                        'bearish_count': 0,
                        'neutral_count': len(news[:30]),
                    },
                    'symbol': symbol,
                }
                chart_b64 = plot_sentiment_analysis(sentiment_data, symbol)
            tool = 'yfinance_news'

        elif chart_type == 'forecast':
            df = yf.download(symbol, period='6mo', auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            predicted_price = float(request.args.get('predicted_price', 0))
            confidence = float(request.args.get('confidence', 0.5))
            if df is not None and not df.empty and predicted_price:
                chart_b64 = plot_forecast(df, predicted_price, symbol, confidence)

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
            **_meta(tool, 90),
        })

    except Exception as exc:
        logger.error("Error in visualize for %s (%s): %s", symbol, chart_type, exc)
        return jsonify({'success': False, 'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# 7. Status check
# ---------------------------------------------------------------------------

@alpha_vantage_bp.route('/status', methods=['GET'])
@login_required
def av_status():
    """Return market data integration status (yfinance)."""
    try:
        ticker = yf.Ticker('MSFT')
        price = ticker.fast_info.get('lastPrice') or ticker.fast_info.get('last_price')
        yfinance_ok = price is not None
    except Exception:
        yfinance_ok = False

    return jsonify({
        'success': True,
        'data_source': 'yfinance',
        'configured': yfinance_ok,
        'tools_available': [
            'yfinance_ticker',
            'yfinance_download',
            'yfinance_info',
            'yfinance_financials',
            'yfinance_balance_sheet',
            'yfinance_cashflow',
            'yfinance_news',
            'yfinance_search',
        ],
    })
