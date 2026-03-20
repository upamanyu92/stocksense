from flask import Blueprint, request, jsonify
from app.services.backtester import run_simple_backtest

backtest_bp = Blueprint('backtest', __name__, url_prefix='/api/backtest')

@backtest_bp.route('/run', methods=['POST'])
def run_backtest():
    data = request.json or {}
    symbol = data.get('symbol')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    initial_capital = float(data.get('initial_capital', 100000))
    strategy = data.get('strategy', {})
    if not symbol or not start_date or not end_date:
        return jsonify({'error': 'symbol, start_date, end_date required'}), 400
    res = run_simple_backtest(symbol, start_date, end_date, initial_capital, strategy)
    return jsonify(res)
