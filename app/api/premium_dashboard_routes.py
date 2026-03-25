"""
Premium Dashboard API routes - provides data for the AI-powered stock analytics dashboard.
"""
import json
import logging
import math
from datetime import datetime, timedelta

import yfinance as yf
import pandas as pd

from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user

from app.utils.util import get_db_connection
from app.db.session_manager import get_session_manager

logger = logging.getLogger(__name__)

# Thresholds for classifying prediction movement direction
BULLISH_THRESHOLD = 2.0   # percent change above which a prediction is "bullish/up"
BEARISH_THRESHOLD = -2.0  # percent change below which a prediction is "bearish/down"

premium_dashboard_bp = Blueprint('premium_dashboard', __name__)


@premium_dashboard_bp.route('/premium')
@login_required
def premium_dashboard():
    """Serve the premium dashboard page"""
    return render_template('premium_dashboard.html', username=current_user.username)


@premium_dashboard_bp.route('/api/dashboard/overview', methods=['GET'])
@login_required
def dashboard_overview():
    """Get portfolio overview with total value, P&L, and summary stats"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get portfolio holdings
        cursor.execute('''
            SELECT COALESCE(SUM(current_value * quantity), 0) as total_value,
                   COALESCE(SUM(invested_value), 0) as total_invested,
                   COALESCE(SUM(pnl), 0) as total_pnl,
                   COUNT(*) as holdings_count
            FROM portfolio_holdings WHERE user_id = ?
        ''', (current_user.id,))
        row = cursor.fetchone()

        total_value = row[0] if row else 0
        total_invested = row[1] if row else 0
        total_pnl = row[2] if row else 0
        holdings_count = row[3] if row else 0
        pnl_percent = ((total_value - total_invested) / total_invested * 100) if total_invested > 0 else 0

        # Get watchlist count
        cursor.execute('SELECT COUNT(*) FROM watchlists WHERE user_id = ?', (current_user.id,))
        watchlist_count = cursor.fetchone()[0]

        # Get predictions count
        cursor.execute('SELECT COUNT(*) FROM predictions WHERE user_id = ?', (current_user.id,))
        predictions_count = cursor.fetchone()[0]

        # Get recent trades count (last 7 days)
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute('SELECT COUNT(*) FROM trades WHERE user_id = ? AND created_at >= ?',
                      (current_user.id, week_ago))
        recent_trades = cursor.fetchone()[0]

        conn.close()

        return jsonify({
            'success': True,
            'overview': {
                'total_value': round(total_value, 2),
                'total_invested': round(total_invested, 2),
                'total_pnl': round(total_pnl, 2),
                'pnl_percent': round(pnl_percent, 2),
                'holdings_count': holdings_count,
                'watchlist_count': watchlist_count,
                'predictions_count': predictions_count,
                'recent_trades': recent_trades
            }
        })
    except Exception as e:
        logger.error(f"Error fetching dashboard overview: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to fetch dashboard overview'}), 500


@premium_dashboard_bp.route('/api/dashboard/market-indices', methods=['GET'])
@login_required
def market_indices():
    """Get live market indices data (NIFTY 50, SENSEX, etc.)"""
    try:
        # Return market data - in production, this would fetch from a live API
        # For now, try to get data from stock_quotes for major indices
        conn = get_db_connection()
        cursor = conn.cursor()

        indices_data = []

        # Try to get some top stocks as representative market data
        cursor.execute('''
            SELECT company_name, security_id, current_value, change, p_change
            FROM stock_quotes
            WHERE current_value > 0
            ORDER BY CAST(REPLACE(REPLACE(market_cap_full, ',', ''), ' ', '') AS REAL) DESC
            LIMIT 5
        ''')
        top_stocks = cursor.fetchall()
        conn.close()

        # Build indices data with market indicators
        market_data = [
            {'name': 'NIFTY 50', 'symbol': '^NSEI', 'value': 22456.80, 'change': 156.30, 'p_change': 0.70, 'type': 'index'},
            {'name': 'SENSEX', 'symbol': '^BSESN', 'value': 73890.45, 'change': 478.20, 'p_change': 0.65, 'type': 'index'},
            {'name': 'BANK NIFTY', 'symbol': '^NSEBANK', 'value': 48234.50, 'change': -123.40, 'p_change': -0.26, 'type': 'index'},
        ]

        # Add top stocks from DB if available
        for stock in top_stocks:
            market_data.append({
                'name': stock[0],
                'symbol': stock[1],
                'value': stock[2] or 0,
                'change': stock[3] or 0,
                'p_change': stock[4] or 0,
                'type': 'stock'
            })

        return jsonify({
            'success': True,
            'indices': market_data
        })
    except Exception as e:
        logger.error(f"Error fetching market indices: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@premium_dashboard_bp.route('/api/dashboard/ai-insights', methods=['GET'])
@login_required
def ai_insights():
    """Get AI-generated insights feed"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get recent AI insights
        cursor.execute('''
            SELECT id, stock_symbol, insight_type, message, confidence, source, created_at
            FROM ai_insights
            ORDER BY created_at DESC
            LIMIT 20
        ''')
        rows = cursor.fetchall()

        insights = []
        if rows:
            for row in rows:
                insights.append({
                    'id': row[0],
                    'stock_symbol': row[1],
                    'insight_type': row[2],
                    'message': row[3],
                    'confidence': row[4],
                    'source': row[5],
                    'created_at': row[6]
                })

        # If no insights in DB, generate some based on predictions
        if not insights:
            cursor.execute('''
                SELECT p.stock_symbol, p.predicted_price, sq.current_value, sq.company_name
                FROM predictions p
                LEFT JOIN stock_quotes sq ON p.stock_symbol = sq.security_id
                WHERE p.predicted_price IS NOT NULL AND sq.current_value IS NOT NULL AND sq.current_value > 0
                ORDER BY p.prediction_date DESC
                LIMIT 10
            ''')
            pred_rows = cursor.fetchall()

            for row in pred_rows:
                symbol = row[0]
                predicted = row[1]
                current = row[2]
                company = row[3] or symbol

                if predicted and current and current > 0:
                    change_pct = ((predicted - current) / current) * 100
                    if change_pct > BULLISH_THRESHOLD:
                        insight_type = 'buy_signal'
                        message = f"{company} likely to rise {abs(change_pct):.1f}% based on AI prediction model"
                        confidence = min(0.65 + abs(change_pct) / 100, 0.95)
                    elif change_pct < BEARISH_THRESHOLD:
                        insight_type = 'sell_signal'
                        message = f"Sell signal detected for {company} — predicted decline of {abs(change_pct):.1f}%"
                        confidence = min(0.60 + abs(change_pct) / 100, 0.92)
                    else:
                        insight_type = 'trend'
                        message = f"{company} expected to remain stable with minimal movement"
                        confidence = 0.55

                    insights.append({
                        'id': len(insights) + 1,
                        'stock_symbol': symbol,
                        'insight_type': insight_type,
                        'message': message,
                        'confidence': round(confidence, 2),
                        'source': 'AI Prediction Engine',
                        'created_at': datetime.now().isoformat()
                    })

        conn.close()

        return jsonify({
            'success': True,
            'insights': insights
        })
    except Exception as e:
        logger.error(f"Error fetching AI insights: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@premium_dashboard_bp.route('/api/dashboard/predictions-summary', methods=['GET'])
@login_required
def predictions_summary():
    """Get AI predictions summary for dashboard cards"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT p.stock_symbol, p.predicted_price, p.prediction_date,
                   sq.current_value, sq.company_name, sq.p_change
            FROM predictions p
            LEFT JOIN stock_quotes sq ON p.stock_symbol = sq.security_id
            WHERE p.predicted_price IS NOT NULL
            ORDER BY p.prediction_date DESC
            LIMIT 20
        ''')
        rows = cursor.fetchall()
        conn.close()

        predictions = []
        for row in rows:
            symbol = row[0]
            predicted = row[1]
            pred_date = row[2]
            current = row[3]
            company = row[4] or symbol
            p_change = row[5] or 0

            if predicted and current and current > 0:
                change_pct = ((predicted - current) / current) * 100
                if change_pct > 1:
                    movement = 'Up'
                elif change_pct < -1:
                    movement = 'Down'
                else:
                    movement = 'Neutral'

                confidence = min(0.55 + abs(change_pct) / 50, 0.95)

                predictions.append({
                    'stock_symbol': symbol,
                    'company_name': company,
                    'current_price': round(current, 2),
                    'predicted_price': round(predicted, 2),
                    'change_percent': round(change_pct, 2),
                    'movement': movement,
                    'confidence': round(confidence, 2),
                    'prediction_date': pred_date,
                    'p_change': round(p_change, 2)
                })

        return jsonify({
            'success': True,
            'predictions': predictions
        })
    except Exception as e:
        logger.error(f"Error fetching predictions summary: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@premium_dashboard_bp.route('/api/dashboard/recent-activity', methods=['GET'])
@login_required
def recent_activity():
    """Get recent trades and activity timeline"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, stock_symbol, company_name, trade_type, quantity, price, total_value, created_at
            FROM trades
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 20
        ''', (current_user.id,))
        rows = cursor.fetchall()
        conn.close()

        trades = []
        for row in rows:
            trades.append({
                'id': row[0],
                'stock_symbol': row[1],
                'company_name': row[2],
                'trade_type': row[3],
                'quantity': row[4],
                'price': row[5],
                'total_value': row[6],
                'created_at': row[7]
            })

        return jsonify({
            'success': True,
            'trades': trades
        })
    except Exception as e:
        logger.error(f"Error fetching recent activity: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@premium_dashboard_bp.route('/api/dashboard/record-trade', methods=['POST'])
@login_required
def record_trade():
    """Record a new trade (buy/sell)"""
    try:
        data = request.get_json()
        stock_symbol = data.get('stock_symbol')
        company_name = data.get('company_name', '')
        trade_type = data.get('trade_type', 'BUY').upper()
        quantity = int(data.get('quantity', 0))
        price = float(data.get('price', 0))

        if not stock_symbol or quantity <= 0 or price <= 0:
            return jsonify({'success': False, 'error': 'Invalid trade parameters'}), 400

        if trade_type not in ('BUY', 'SELL'):
            return jsonify({'success': False, 'error': 'trade_type must be BUY or SELL'}), 400

        total_value = quantity * price

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trades (user_id, stock_symbol, company_name, trade_type, quantity, price, total_value)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (current_user.id, stock_symbol, company_name, trade_type, quantity, price, total_value))
        conn.commit()

        # Update portfolio holdings
        if trade_type == 'BUY':
            # Check if holding exists
            cursor.execute('SELECT id, quantity, avg_buy_price, invested_value FROM portfolio_holdings WHERE user_id = ? AND stock_symbol = ?',
                         (current_user.id, stock_symbol))
            existing = cursor.fetchone()

            if existing:
                new_qty = existing[1] + quantity
                new_invested = existing[3] + total_value
                new_avg = new_invested / new_qty if new_qty > 0 else 0
                new_pnl = (price * new_qty) - new_invested
                new_pnl_pct = (new_pnl / new_invested * 100) if new_invested > 0 else 0
                cursor.execute('''
                    UPDATE portfolio_holdings
                    SET quantity = ?, avg_buy_price = ?, invested_value = ?,
                        current_value = ?, pnl = ?, pnl_percent = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                ''', (new_qty, new_avg, new_invested, price, new_pnl, new_pnl_pct, existing[0]))
            else:
                cursor.execute('''
                    INSERT INTO portfolio_holdings (user_id, stock_symbol, company_name, quantity, avg_buy_price, current_value, invested_value, pnl, pnl_percent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)
                ''', (current_user.id, stock_symbol, company_name, quantity, price, price, total_value))
        elif trade_type == 'SELL':
            cursor.execute('SELECT id, quantity, invested_value FROM portfolio_holdings WHERE user_id = ? AND stock_symbol = ?',
                         (current_user.id, stock_symbol))
            existing = cursor.fetchone()
            if existing:
                new_qty = max(existing[1] - quantity, 0)
                if new_qty == 0:
                    cursor.execute('DELETE FROM portfolio_holdings WHERE id = ?', (existing[0],))
                else:
                    ratio = new_qty / existing[1] if existing[1] > 0 else 0
                    new_invested = existing[2] * ratio
                    cursor.execute('''
                        UPDATE portfolio_holdings SET quantity = ?, invested_value = ?, updated_at = datetime('now')
                        WHERE id = ?
                    ''', (new_qty, new_invested, existing[0]))

        conn.commit()
        conn.close()

        # Update user XP for trading
        _update_user_xp(current_user.id, 10, 'trade')

        return jsonify({'success': True, 'message': f'{trade_type} order recorded successfully'})
    except Exception as e:
        logger.error(f"Error recording trade: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@premium_dashboard_bp.route('/api/dashboard/portfolio', methods=['GET'])
@login_required
def get_portfolio():
    """Get user's portfolio holdings"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, stock_symbol, company_name, quantity, avg_buy_price,
                   current_value, invested_value, pnl, pnl_percent, updated_at
            FROM portfolio_holdings
            WHERE user_id = ?
            ORDER BY invested_value DESC
        ''', (current_user.id,))
        rows = cursor.fetchall()
        conn.close()

        holdings = []
        for row in rows:
            holdings.append({
                'id': row[0],
                'stock_symbol': row[1],
                'company_name': row[2],
                'quantity': row[3],
                'avg_buy_price': row[4],
                'current_value': row[5],
                'invested_value': row[6],
                'pnl': row[7],
                'pnl_percent': row[8],
                'updated_at': row[9]
            })

        return jsonify({'success': True, 'holdings': holdings})
    except Exception as e:
        logger.error(f"Error fetching portfolio: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@premium_dashboard_bp.route('/api/dashboard/user-level', methods=['GET'])
@login_required
def user_level():
    """Get user's gamification level and stats"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM user_levels WHERE user_id = ?', (current_user.id,))
        row = cursor.fetchone()

        if not row:
            # Create default level entry
            cursor.execute('''
                INSERT INTO user_levels (user_id, level_name, xp_points, predictions_made, successful_predictions, streak_days, badges)
                VALUES (?, 'Smart Investor', 0, 0, 0, 0, '[]')
            ''', (current_user.id,))
            conn.commit()
            level_data = {
                'level_name': 'Smart Investor',
                'xp_points': 0,
                'predictions_made': 0,
                'successful_predictions': 0,
                'streak_days': 0,
                'badges': []
            }
        else:
            badges = []
            try:
                badges = json.loads(row[7]) if row[7] else []
            except (json.JSONDecodeError, TypeError):
                badges = []

            level_data = {
                'level_name': row[2],
                'xp_points': row[3],
                'predictions_made': row[4],
                'successful_predictions': row[5],
                'streak_days': row[6],
                'badges': badges
            }

        # Determine level based on XP
        xp = level_data['xp_points']
        if xp >= 1000:
            level_data['level_name'] = 'Market Pro'
            level_data['level_tier'] = 3
        elif xp >= 500:
            level_data['level_name'] = 'AI Trader'
            level_data['level_tier'] = 2
        else:
            level_data['level_name'] = 'Smart Investor'
            level_data['level_tier'] = 1

        level_data['next_level_xp'] = 500 if xp < 500 else (1000 if xp < 1000 else 2000)
        if xp < 500:
            level_data['xp_progress'] = xp / 500 * 100
        elif xp < 1000:
            level_data['xp_progress'] = (xp - 500) / 500 * 100
        else:
            level_data['xp_progress'] = (xp - 1000) / 1000 * 100

        conn.close()

        return jsonify({
            'success': True,
            'level': level_data
        })
    except Exception as e:
        logger.error(f"Error fetching user level: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@premium_dashboard_bp.route('/api/dashboard/sentiment', methods=['GET'])
@login_required
def get_sentiment():
    """Get market sentiment analysis"""
    try:
        symbol = request.args.get('symbol', '')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get recent predictions to derive sentiment
        if symbol:
            cursor.execute('''
                SELECT p.stock_symbol, p.predicted_price, sq.current_value, sq.company_name
                FROM predictions p
                LEFT JOIN stock_quotes sq ON p.stock_symbol = sq.security_id
                WHERE p.stock_symbol = ? AND p.predicted_price IS NOT NULL AND sq.current_value > 0
                ORDER BY p.prediction_date DESC LIMIT 5
            ''', (symbol,))
        else:
            cursor.execute('''
                SELECT p.stock_symbol, p.predicted_price, sq.current_value, sq.company_name
                FROM predictions p
                LEFT JOIN stock_quotes sq ON p.stock_symbol = sq.security_id
                WHERE p.predicted_price IS NOT NULL AND sq.current_value > 0
                ORDER BY p.prediction_date DESC LIMIT 20
            ''')

        rows = cursor.fetchall()
        conn.close()

        bullish_count = 0
        bearish_count = 0
        neutral_count = 0

        for row in rows:
            predicted = row[1]
            current = row[2]
            if predicted and current and current > 0:
                change = ((predicted - current) / current) * 100
                if change > BULLISH_THRESHOLD / 2:
                    bullish_count += 1
                elif change < BEARISH_THRESHOLD / 2:
                    bearish_count += 1
                else:
                    neutral_count += 1

        total = bullish_count + bearish_count + neutral_count
        if total > 0:
            sentiment_score = (bullish_count - bearish_count) / total
            if sentiment_score > 0.2:
                overall = 'Bullish'
            elif sentiment_score < -0.2:
                overall = 'Bearish'
            else:
                overall = 'Neutral'
        else:
            sentiment_score = 0
            overall = 'Neutral'

        return jsonify({
            'success': True,
            'sentiment': {
                'overall': overall,
                'score': round(sentiment_score, 2),
                'bullish_count': bullish_count,
                'bearish_count': bearish_count,
                'neutral_count': neutral_count,
                'total_analyzed': total
            }
        })
    except Exception as e:
        logger.error(f"Error fetching sentiment: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@premium_dashboard_bp.route('/api/dashboard/sector-heatmap', methods=['GET'])
@login_required
def sector_heatmap():
    """Get sector-wise performance data for heatmap visualization"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT industry,
                   COUNT(*) as stock_count,
                   AVG(p_change) as avg_change,
                   SUM(CASE WHEN p_change > 0 THEN 1 ELSE 0 END) as gainers,
                   SUM(CASE WHEN p_change < 0 THEN 1 ELSE 0 END) as losers
            FROM stock_quotes
            WHERE industry IS NOT NULL AND industry != '' AND current_value > 0
            GROUP BY industry
            ORDER BY avg_change DESC
        ''')
        rows = cursor.fetchall()
        conn.close()

        sectors = []
        for row in rows:
            sectors.append({
                'name': row[0],
                'stock_count': row[1],
                'avg_change': round(row[2], 2) if row[2] else 0,
                'gainers': row[3],
                'losers': row[4]
            })

        return jsonify({
            'success': True,
            'sectors': sectors
        })
    except Exception as e:
        logger.error(f"Error fetching sector heatmap: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


def _update_user_xp(user_id, xp_amount, action_type):
    """Internal helper to update user XP points"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id, xp_points FROM user_levels WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()

        if row:
            new_xp = row[1] + xp_amount
            # Determine new level name
            if new_xp >= 1000:
                level_name = 'Market Pro'
            elif new_xp >= 500:
                level_name = 'AI Trader'
            else:
                level_name = 'Smart Investor'

            cursor.execute('''
                UPDATE user_levels SET xp_points = ?, level_name = ?, updated_at = datetime('now')
                WHERE user_id = ?
            ''', (new_xp, level_name, user_id))
        else:
            cursor.execute('''
                INSERT INTO user_levels (user_id, level_name, xp_points) VALUES (?, 'Smart Investor', ?)
            ''', (user_id, xp_amount))

        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error updating user XP: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Helper: resolve stock symbol to yfinance ticker (try .NS then .BO then raw)
# ---------------------------------------------------------------------------

def _resolve_yf_symbol(symbol: str) -> str:
    """Return the symbol as-is if it already has a suffix, otherwise append .NS."""
    sym = symbol.strip().upper()
    if '.' in sym:
        return sym
    return sym + '.NS'


def _compute_sma(closes, period):
    """Return list of (date, sma) tuples; None for insufficient history."""
    result = []
    for i, (date, val) in enumerate(closes):
        if i < period - 1:
            result.append({'x': date, 'y': None})
        else:
            window = [v for _, v in closes[i - period + 1:i + 1]]
            result.append({'x': date, 'y': round(sum(window) / period, 2)})
    return result


def _compute_rsi(closes, period=14):
    """Compute RSI on a list of close prices."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [abs(min(d, 0)) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _compute_macd(closes):
    """Return (macd, signal, histogram) or None."""
    if len(closes) < 35:
        return None

    def ema(data, span):
        k = 2 / (span + 1)
        result = [data[0]]
        for v in data[1:]:
            result.append(v * k + result[-1] * (1 - k))
        return result

    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    macd_line = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    signal_line = ema(macd_line[25:], 9)
    macd_val = macd_line[-1]
    signal_val = signal_line[-1] if signal_line else 0
    histogram = macd_val - signal_val
    return round(macd_val, 4), round(signal_val, 4), round(histogram, 4)


# ---------------------------------------------------------------------------
# NEW: Candlestick chart data
# ---------------------------------------------------------------------------

@premium_dashboard_bp.route('/api/dashboard/candlestick/<path:symbol>', methods=['GET'])
@login_required
def get_candlestick(symbol):
    """Return OHLCV candles + SMA-20 for the TradingView Lightweight chart."""
    period = request.args.get('period', '3mo')
    interval = request.args.get('interval', '1d')
    try:
        ticker_sym = _resolve_yf_symbol(symbol)
        df = yf.download(ticker_sym, period=period, interval=interval,
                         auto_adjust=True, progress=False)

        # Fallback to .BO suffix if .NS returned nothing
        if (df is None or df.empty) and ticker_sym.endswith('.NS'):
            ticker_sym = symbol.strip().upper() + '.BO'
            df = yf.download(ticker_sym, period=period, interval=interval,
                             auto_adjust=True, progress=False)

        if df is None or df.empty:
            return jsonify({'success': False, 'error': f'No data for {symbol}'}), 404

        # Flatten multi-level columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        candles = []
        closes_with_dates = []
        for idx, row in df.iterrows():
            date_str = str(idx.date())
            candles.append({
                'x': date_str,
                'o': round(float(row['Open']), 2),
                'h': round(float(row['High']), 2),
                'l': round(float(row['Low']), 2),
                'c': round(float(row['Close']), 2),
                'v': int(row['Volume']),
            })
            closes_with_dates.append((date_str, float(row['Close'])))

        sma20 = _compute_sma(closes_with_dates, 20)

        return jsonify({
            'success': True,
            'symbol': symbol,
            'candles': candles,
            'sma20': sma20,
        })
    except Exception as e:
        logger.error(f"Error fetching candlestick for {symbol}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------------------------------------------------------------------------
# NEW: Technical indicators with plain-English translation
# ---------------------------------------------------------------------------

@premium_dashboard_bp.route('/api/dashboard/technical-indicators/<path:symbol>', methods=['GET'])
@login_required
def get_technical_indicators(symbol):
    """Compute RSI, MACD, SMA-20/50, Bollinger Bands for a symbol."""
    try:
        ticker_sym = _resolve_yf_symbol(symbol)
        df = yf.download(ticker_sym, period='6mo', interval='1d',
                         auto_adjust=True, progress=False)
        if (df is None or df.empty) and ticker_sym.endswith('.NS'):
            ticker_sym = symbol.strip().upper() + '.BO'
            df = yf.download(ticker_sym, period='6mo', interval='1d',
                             auto_adjust=True, progress=False)

        if df is None or df.empty:
            return jsonify({'success': False, 'error': f'No data for {symbol}'}), 404

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        closes = [float(v) for v in df['Close'].tolist()]
        current_price = closes[-1] if closes else 0

        indicators = []
        signals = []

        # RSI
        rsi = _compute_rsi(closes)
        if rsi is not None:
            if rsi > 70:
                rsi_signal, rsi_plain = 'bearish', 'Overbought — price has risen too fast'
            elif rsi < 30:
                rsi_signal, rsi_plain = 'bullish', 'Oversold — potential buying opportunity'
            else:
                rsi_signal, rsi_plain = 'neutral', 'Neutral zone — no extreme signals'
            signals.append(rsi_signal)
            indicators.append({
                'name': 'RSI (14)',
                'emoji': '📊',
                'value': f'{rsi:.1f}',
                'signal': rsi_signal,
                'plain_english': rsi_plain,
                'why': 'RSI measures momentum. >70 = overbought, <30 = oversold.',
            })

        # MACD
        macd_result = _compute_macd(closes)
        if macd_result:
            macd_val, signal_val, histogram = macd_result
            if histogram > 0:
                macd_signal, macd_plain = 'bullish', 'MACD above signal line — upward momentum'
            else:
                macd_signal, macd_plain = 'bearish', 'MACD below signal line — downward momentum'
            signals.append(macd_signal)
            indicators.append({
                'name': 'MACD',
                'emoji': '📈',
                'value': f'{macd_val:.3f}',
                'signal': macd_signal,
                'plain_english': macd_plain,
                'why': 'MACD shows trend direction and momentum. Positive histogram = bullish.',
            })

        # SMA 20
        if len(closes) >= 20:
            sma20 = sum(closes[-20:]) / 20
            if current_price > sma20:
                sma20_signal, sma20_plain = 'bullish', f'Price above 20-day average (₹{sma20:.2f})'
            else:
                sma20_signal, sma20_plain = 'bearish', f'Price below 20-day average (₹{sma20:.2f})'
            signals.append(sma20_signal)
            indicators.append({
                'name': 'SMA 20',
                'emoji': '📉',
                'value': f'₹{sma20:.2f}',
                'signal': sma20_signal,
                'plain_english': sma20_plain,
                'why': 'Short-term trend indicator. Price above SMA = uptrend.',
            })

        # SMA 50
        if len(closes) >= 50:
            sma50 = sum(closes[-50:]) / 50
            if current_price > sma50:
                sma50_signal, sma50_plain = 'bullish', f'Price above 50-day average (₹{sma50:.2f})'
            else:
                sma50_signal, sma50_plain = 'bearish', f'Price below 50-day average (₹{sma50:.2f})'
            signals.append(sma50_signal)
            indicators.append({
                'name': 'SMA 50',
                'emoji': '🎯',
                'value': f'₹{sma50:.2f}',
                'signal': sma50_signal,
                'plain_english': sma50_plain,
                'why': 'Medium-term trend indicator. Golden cross (SMA20>SMA50) = bullish.',
            })

        # Bollinger Bands (20-day, 2σ)
        if len(closes) >= 20:
            window = closes[-20:]
            mean = sum(window) / 20
            std = math.sqrt(sum((v - mean) ** 2 for v in window) / 20)
            upper_bb = mean + 2 * std
            lower_bb = mean - 2 * std
            if current_price > upper_bb:
                bb_signal, bb_plain = 'bearish', 'Price above upper Bollinger Band — stretched'
            elif current_price < lower_bb:
                bb_signal, bb_plain = 'bullish', 'Price below lower Bollinger Band — potential reversal'
            else:
                bb_signal, bb_plain = 'neutral', f'Price within bands (₹{lower_bb:.2f}–₹{upper_bb:.2f})'
            signals.append(bb_signal)
            indicators.append({
                'name': 'Bollinger Bands',
                'emoji': '🎪',
                'value': f'₹{lower_bb:.2f}–₹{upper_bb:.2f}',
                'signal': bb_signal,
                'plain_english': bb_plain,
                'why': 'Bands show volatility. Breaking bands signals potential trend change.',
            })

        bullish = signals.count('bullish')
        bearish = signals.count('bearish')
        if bullish > bearish:
            overall = 'Bullish'
        elif bearish > bullish:
            overall = 'Bearish'
        else:
            overall = 'Neutral'

        return jsonify({
            'success': True,
            'symbol': symbol,
            'overall_signal': overall,
            'indicators': indicators,
        })
    except Exception as e:
        logger.error(f"Error fetching technical indicators for {symbol}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------------------------------------------------------------------------
# NEW: Agent reasoning debate (Bull / Bear / Skeptic)
# ---------------------------------------------------------------------------

@premium_dashboard_bp.route('/api/dashboard/agent-reasoning/<path:symbol>', methods=['GET'])
@login_required
def get_agent_reasoning(symbol):
    """Generate a deterministic bull/bear/skeptic agent debate from technical data."""
    try:
        ticker_sym = _resolve_yf_symbol(symbol)
        df = yf.download(ticker_sym, period='6mo', interval='1d',
                         auto_adjust=True, progress=False)
        if (df is None or df.empty) and ticker_sym.endswith('.NS'):
            ticker_sym = symbol.strip().upper() + '.BO'
            df = yf.download(ticker_sym, period='6mo', interval='1d',
                             auto_adjust=True, progress=False)

        if df is None or df.empty:
            return jsonify({'success': False, 'error': f'No data for {symbol}'}), 404

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        closes = [float(v) for v in df['Close'].tolist()]
        current_price = closes[-1] if closes else 0
        week_ago_price = closes[-5] if len(closes) >= 5 else closes[0]
        month_ago_price = closes[-22] if len(closes) >= 22 else closes[0]

        week_change_pct = ((current_price - week_ago_price) / week_ago_price * 100) if week_ago_price else 0
        month_change_pct = ((current_price - month_ago_price) / month_ago_price * 100) if month_ago_price else 0

        rsi = _compute_rsi(closes) or 50
        macd_result = _compute_macd(closes)
        macd_positive = (macd_result[2] > 0) if macd_result else True

        sma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current_price
        above_sma20 = current_price > sma20

        # Bull agent
        bull_args = []
        bull_conf = 50
        if week_change_pct > 2:
            bull_args.append(f'Strong weekly gain of +{week_change_pct:.1f}% shows buying momentum')
            bull_conf += 10
        if rsi < 65 and rsi > 40:
            bull_args.append(f'RSI at {rsi:.0f} — still room to run before overbought')
            bull_conf += 8
        if above_sma20:
            bull_args.append(f'Trading above 20-day SMA (₹{sma20:.2f}) — uptrend intact')
            bull_conf += 10
        if macd_positive:
            bull_args.append('MACD histogram positive — upward momentum confirmed')
            bull_conf += 8
        if month_change_pct > 5:
            bull_args.append(f'Monthly trend +{month_change_pct:.1f}% — institutional interest')
            bull_conf += 6
        if not bull_args:
            bull_args = ['Long-term fundamentals remain intact', 'Market dips are buying opportunities']
        bull_conf = min(bull_conf, 92)

        # Bear agent
        bear_args = []
        bear_conf = 50
        if week_change_pct < -2:
            bear_args.append(f'Weekly decline of {week_change_pct:.1f}% signals selling pressure')
            bear_conf += 10
        if rsi > 68:
            bear_args.append(f'RSI at {rsi:.0f} — overbought territory, correction likely')
            bear_conf += 12
        if not above_sma20:
            bear_args.append(f'Price below 20-day SMA (₹{sma20:.2f}) — downtrend in play')
            bear_conf += 10
        if not macd_positive:
            bear_args.append('MACD turning negative — momentum fading')
            bear_conf += 8
        if month_change_pct < -5:
            bear_args.append(f'Monthly decline of {month_change_pct:.1f}% — distribution phase')
            bear_conf += 8
        if not bear_args:
            bear_args = ['Valuation appears stretched at current levels', 'Market uncertainty remains elevated']
        bear_conf = min(bear_conf, 88)

        # Skeptic
        skeptic_args = [
            'Technical signals are mixed — no clear edge',
            'Market conditions can reverse rapidly',
            'Risk-adjusted returns must be considered before entry',
        ]
        skeptic_conf = 60

        verdict = 'Bull' if bull_conf >= bear_conf else 'Bear'
        conf_diff = abs(bull_conf - bear_conf)
        if conf_diff < 10:
            verdict_summary = 'Agents are closely divided — proceed with caution and tight stop-loss'
        elif verdict == 'Bull':
            verdict_summary = f'Bullish edge with {conf_diff:.0f}pt conviction advantage — consider managed entry'
        else:
            verdict_summary = f'Bearish edge with {conf_diff:.0f}pt conviction advantage — wait for reversal signals'

        return jsonify({
            'success': True,
            'symbol': symbol,
            'debate': {
                'verdict': verdict,
                'verdict_summary': verdict_summary,
                'agents': [
                    {
                        'id': 'bull',
                        'name': 'Bull Agent',
                        'avatar': '🐂',
                        'stance': 'Bullish',
                        'color': '#00ff87',
                        'summary': f'{symbol} showing bullish signals with upside potential',
                        'arguments': bull_args,
                        'confidence_pct': bull_conf,
                        'evidence_grade': 'High' if bull_conf > 75 else 'Medium',
                        'evidence_sources': len(bull_args),
                    },
                    {
                        'id': 'bear',
                        'name': 'Bear Agent',
                        'avatar': '🐻',
                        'stance': 'Bearish',
                        'color': '#ff4757',
                        'summary': f'{symbol} facing headwinds — downside risk present',
                        'arguments': bear_args,
                        'confidence_pct': bear_conf,
                        'evidence_grade': 'High' if bear_conf > 75 else 'Medium',
                        'evidence_sources': len(bear_args),
                    },
                    {
                        'id': 'skeptic',
                        'name': 'Skeptic Agent',
                        'avatar': '🤔',
                        'stance': 'Neutral',
                        'color': '#ffaa00',
                        'summary': 'Mixed evidence — risk management is paramount',
                        'arguments': skeptic_args,
                        'confidence_pct': skeptic_conf,
                        'evidence_grade': 'Medium',
                        'evidence_sources': len(skeptic_args),
                    },
                ],
            },
        })
    except Exception as e:
        logger.error(f"Error in agent reasoning for {symbol}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------------------------------------------------------------------------
# NEW: Portfolio risk meter
# ---------------------------------------------------------------------------

@premium_dashboard_bp.route('/api/dashboard/risk-meter', methods=['GET'])
@login_required
def get_risk_meter():
    """Compute portfolio concentration and volatility risk score (0-100)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT stock_symbol, invested_value, pnl_percent
            FROM portfolio_holdings
            WHERE user_id = ?
        ''', (current_user.id,))
        holdings = cursor.fetchall()
        conn.close()

        if not holdings:
            return jsonify({
                'success': True,
                'risk': {
                    'score': 0,
                    'label': 'No Holdings',
                    'color': '#aaa',
                    'icon': '📭',
                    'message': 'Add portfolio holdings to see your risk score',
                    'breakdown': [],
                }
            })

        total_invested = sum(h[1] or 0 for h in holdings)
        n = len(holdings)

        # Concentration risk: Herfindahl index (0=diversified, 1=concentrated)
        hhi = sum(((h[1] or 0) / total_invested) ** 2 for h in holdings) if total_invested else 1
        concentration_score = round(hhi * 40, 1)  # max 40 pts

        # Drawdown risk: average negative PnL%
        neg_pnls = [abs(h[2]) for h in holdings if (h[2] or 0) < -5]
        drawdown_score = min(round(sum(neg_pnls) / max(n, 1), 1), 30.0)  # max 30 pts

        # Diversification bonus: fewer holdings = more risk
        div_score = max(0, round(30 - n * 3, 1))  # max 30 pts

        total_score = min(round(concentration_score + drawdown_score + div_score, 0), 100)

        if total_score >= 70:
            label, color, icon = 'High Risk', '#ff4757', '🔴'
        elif total_score >= 40:
            label, color, icon = 'Moderate Risk', '#ffaa00', '🟡'
        else:
            label, color, icon = 'Low Risk', '#00ff87', '🟢'

        return jsonify({
            'success': True,
            'risk': {
                'score': int(total_score),
                'label': label,
                'color': color,
                'icon': icon,
                'message': f'Portfolio of {n} holding(s) with {label.lower()} profile',
                'breakdown': [
                    {'label': 'Concentration Risk', 'score': concentration_score,
                     'detail': f'HHI: {hhi:.2f} — {"highly concentrated" if hhi > 0.5 else "well diversified"}'},
                    {'label': 'Drawdown Exposure', 'score': drawdown_score,
                     'detail': f'{len(neg_pnls)} holding(s) down >5%'},
                    {'label': 'Diversification Gap', 'score': div_score,
                     'detail': f'{n} stock(s) — aim for 10+ to reduce risk'},
                ],
            }
        })
    except Exception as e:
        logger.error(f"Error computing risk meter: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------------------------------------------------------------------------
# NEW: Kill criteria checker (single stock)
# ---------------------------------------------------------------------------

@premium_dashboard_bp.route('/api/dashboard/kill-criteria/<path:symbol>', methods=['GET'])
@login_required
def check_kill_criteria(symbol):
    """Check if a stock has breached kill criteria thresholds."""
    try:
        ticker_sym = _resolve_yf_symbol(symbol)
        df = yf.download(ticker_sym, period='1mo', interval='1d',
                         auto_adjust=True, progress=False)
        if (df is None or df.empty) and ticker_sym.endswith('.NS'):
            ticker_sym = symbol.strip().upper() + '.BO'
            df = yf.download(ticker_sym, period='1mo', interval='1d',
                             auto_adjust=True, progress=False)

        if df is None or df.empty:
            return jsonify({'success': True, 'triggered': False, 'reasons': []})

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        closes = [float(v) for v in df['Close'].tolist()]
        current_price = closes[-1]
        month_high = max(closes)
        drawdown_pct = ((month_high - current_price) / month_high * 100) if month_high else 0

        rsi = _compute_rsi(closes)
        reasons = []
        triggered = False

        if drawdown_pct >= 15:
            reasons.append(f'Price drew down {drawdown_pct:.1f}% from recent high')
            triggered = True
        if rsi is not None and rsi < 25:
            reasons.append(f'RSI critically oversold at {rsi:.0f}')
            triggered = True
        if len(closes) >= 5:
            five_day_change = (closes[-1] - closes[-5]) / closes[-5] * 100
            if five_day_change < -10:
                reasons.append(f'5-day price drop of {five_day_change:.1f}%')
                triggered = True

        notification = None
        if triggered:
            notification = {
                'title': f'Kill Criterion: {symbol}',
                'body': reasons[0] if reasons else 'Threshold breached',
            }

        return jsonify({
            'success': True,
            'triggered': triggered,
            'reasons': reasons,
            'notification': notification,
        })
    except Exception as e:
        logger.error(f"Error in kill criteria for {symbol}: {e}", exc_info=True)
        return jsonify({'success': True, 'triggered': False, 'reasons': []})


# ---------------------------------------------------------------------------
# NEW: Kill criteria batch (watchlist)
# ---------------------------------------------------------------------------

@premium_dashboard_bp.route('/api/dashboard/kill-criteria-batch', methods=['GET'])
@login_required
def check_kill_criteria_batch():
    """Batch kill-criteria check for all watchlist stocks."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT stock_symbol FROM watchlists WHERE user_id = ?', (current_user.id,))
        rows = cursor.fetchall()
        conn.close()

        triggered_items = []
        for row in rows[:10]:  # Limit to 10 to avoid rate limits
            sym = row[0]
            try:
                ticker_sym = _resolve_yf_symbol(sym)
                df = yf.download(ticker_sym, period='5d', interval='1d',
                                 auto_adjust=True, progress=False)
                if (df is None or df.empty) and ticker_sym.endswith('.NS'):
                    df = yf.download(sym.upper() + '.BO', period='5d', interval='1d',
                                     auto_adjust=True, progress=False)
                if df is None or df.empty:
                    continue
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                closes = [float(v) for v in df['Close'].tolist()]
                if len(closes) >= 2:
                    chg = (closes[-1] - closes[0]) / closes[0] * 100
                    if chg < -10:
                        triggered_items.append({
                            'symbol': sym,
                            'message': f'{sym} down {chg:.1f}% in 5 days',
                            'severity': 'critical',
                        })
            except Exception:
                continue

        return jsonify({
            'success': True,
            'triggered': triggered_items,
        })
    except Exception as e:
        logger.error(f"Error in kill criteria batch: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------------------------------------------------------------------------
# NEW: Alerts feed
# ---------------------------------------------------------------------------

@premium_dashboard_bp.route('/api/dashboard/alerts-feed', methods=['GET'])
@login_required
def get_alerts_feed():
    """Return recent notifications/alerts for the current user."""
    try:
        db = get_session_manager()

        # Fetch notifications scoped to this user (or global ones with user_id IS NULL)
        notifs = db.fetch_all('''
            SELECT n.id, n.symbol, n.message, n.sent, n.created_at, a.condition_type
            FROM notifications n
            LEFT JOIN alerts a ON n.alert_id = a.id
            WHERE n.user_id = ? OR n.user_id IS NULL
            ORDER BY n.created_at DESC
            LIMIT 30
        ''', (current_user.id,))

        alerts = []
        kill_count = 0
        for n in notifs:
            ctype = n.get('condition_type', '') or ''
            is_kill = 'kill' in ctype.lower()
            if is_kill:
                kill_count += 1
            alerts.append({
                'id': n.get('id'),
                'symbol': n.get('symbol', ''),
                'message': n.get('message', ''),
                'type': ctype or 'Alert',
                'severity': 'critical' if is_kill else ('high' if n.get('sent') == 0 else 'low'),
                'is_kill_criteria': is_kill,
                'timestamp': n.get('created_at'),
            })

        return jsonify({
            'success': True,
            'alerts': alerts,
            'kill_criteria_count': kill_count,
        })
    except Exception as e:
        logger.error(f"Error fetching alerts feed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------------------------------------------------------------------------
# NEW: Paper trade simulation
# ---------------------------------------------------------------------------

@premium_dashboard_bp.route('/api/dashboard/paper-trade', methods=['POST'])
@login_required
def paper_trade():
    """Simulate a paper exit trade: computes P&L against portfolio average buy price."""
    try:
        data = request.get_json() or {}
        symbol = (data.get('symbol') or '').strip().upper()
        qty = int(data.get('quantity') or 0)
        exit_price_override = data.get('exit_price')

        if not symbol:
            return jsonify({'success': False, 'error': 'Symbol is required'}), 400

        # Fetch portfolio holding for this symbol
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT company_name, quantity, avg_buy_price, invested_value
            FROM portfolio_holdings
            WHERE user_id = ? AND stock_symbol = ?
        ''', (current_user.id, symbol))
        holding = cursor.fetchone()
        conn.close()

        avg_buy_price = float(holding[2]) if holding else 0
        portfolio_qty = int(holding[1]) if holding else 0
        company_name = holding[0] if holding else symbol

        if qty <= 0:
            qty = portfolio_qty or 1

        # Resolve current market price
        exit_price = None
        if exit_price_override:
            exit_price = float(exit_price_override)
        else:
            try:
                ticker_sym = _resolve_yf_symbol(symbol)
                tk = yf.Ticker(ticker_sym)
                info = tk.fast_info
                exit_price = float(info.get('lastPrice') or info.get('regularMarketPrice') or 0)
                if not exit_price and ticker_sym.endswith('.NS'):
                    tk2 = yf.Ticker(symbol + '.BO')
                    info2 = tk2.fast_info
                    exit_price = float(info2.get('lastPrice') or info2.get('regularMarketPrice') or 0)
            except Exception:
                exit_price = 0

        if not exit_price and avg_buy_price:
            exit_price = avg_buy_price  # fallback to cost basis

        if not exit_price:
            return jsonify({'success': False, 'error': 'Could not determine exit price'}), 400

        gross_pnl = (exit_price - avg_buy_price) * qty if avg_buy_price else 0
        pnl_pct = ((exit_price - avg_buy_price) / avg_buy_price * 100) if avg_buy_price else 0

        # Simplified tax estimate: 15% STCG (Short Term Capital Gains) for illustrative
        # purposes only. LTCG (>1yr holding) is taxed at 10% above ₹1L. Consult a tax
        # adviser for actual liability.
        tax_estimate = max(gross_pnl * 0.15, 0)
        net_proceeds = exit_price * qty - tax_estimate

        recommendation = (
            f'Simulated exit at ₹{exit_price:.2f} yields '
            f'{"a profit" if gross_pnl >= 0 else "a loss"} of '
            f'₹{abs(gross_pnl):.2f} ({pnl_pct:+.2f}%). '
            f'{"Consider holding for long-term gains to reduce tax." if 0 < pnl_pct < 20 else ""}'
        )

        return jsonify({
            'success': True,
            'simulation': {
                'symbol': symbol,
                'company': company_name,
                'avg_buy_price': round(avg_buy_price, 2),
                'exit_price': round(exit_price, 2),
                'quantity': qty,
                'gross_pnl': round(gross_pnl, 2),
                'pnl_pct': round(pnl_pct, 2),
                'tax_estimate': round(tax_estimate, 2),
                'net_proceeds': round(net_proceeds, 2),
                'recommendation': recommendation,
                'disclaimer': 'This is a simulation only. No real trade is executed.',
            }
        })
    except Exception as e:
        logger.error(f"Error in paper trade for {data.get('symbol')}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

