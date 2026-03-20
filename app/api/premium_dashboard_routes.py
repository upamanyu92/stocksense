"""
Premium Dashboard API routes - provides data for the AI-powered stock analytics dashboard.
"""
import json
import logging
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user

from app.utils.util import get_db_connection

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
        return jsonify({'success': False, 'error': str(e)}), 500


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
