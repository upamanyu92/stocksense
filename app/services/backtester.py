from typing import List, Dict, Any
from datetime import datetime
from app.db.session_manager import get_session_manager


def run_simple_backtest(symbol: str, start_date: str, end_date: str, initial_capital: float = 100000.0, strategy: Dict[str, Any] = None) -> Dict[str, Any]:
    """Run a simple backtest using stored historical prices in stock_quotes or predictions.
    Strategy is a dict: {'type': 'predicted_change_threshold', 'threshold': 2.5}
    This is a lightweight simulator for demo purposes.
    """
    db = get_session_manager()
    rows = db.fetch_all(
        "SELECT prediction_date, predicted_price FROM predictions "
        "WHERE stock_symbol = ? AND prediction_date BETWEEN ? AND ? "
        "ORDER BY prediction_date",
        (symbol, start_date, end_date),
    )

    if not rows:
        return {'error': 'No prediction data available for backtesting'}

    # Very simple strategy: buy at close when predicted change > threshold, sell next day at next predicted price
    threshold = strategy.get('threshold', 2.0) if strategy else 2.0
    cash = initial_capital
    current_position_quantity = 0.0
    entry_price = 0.0
    trades = []

    for day_index in range(len(rows)-1):
        date, predicted = rows[day_index]
        next_date, next_pred = rows[day_index+1]
        # We need current price - for demo we use predicted as proxy
        current_price = float(predicted)
        next_price = float(next_pred)
        change_pct = ((next_price - current_price) / current_price) * 100
        if change_pct > threshold and cash > 0:
            # buy full position
            qty = cash / current_price
            current_position_quantity = qty
            entry_price = current_price
            cash = 0.0
            trades.append({'action': 'buy', 'date': date, 'price': current_price, 'qty': qty})
        elif current_position_quantity > 0:
            # sell
            cash = current_position_quantity * next_price
            trades.append({'action': 'sell', 'date': next_date, 'price': next_price, 'qty': current_position_quantity})
            current_position_quantity = 0.0
            entry_price = 0.0

    portfolio_value = cash + (current_position_quantity * entry_price if current_position_quantity > 0 else 0.0)
    return {
        'symbol': symbol,
        'start_date': start_date,
        'end_date': end_date,
        'initial_capital': initial_capital,
        'final_value': portfolio_value,
        'trades': trades
    }
