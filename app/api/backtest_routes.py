from flask import Blueprint, request, jsonify
from app.services.backtester import run_simple_backtest

backtest_bp = Blueprint('backtest', __name__, url_prefix='/api/backtest')

@backtest_bp.route('/run', methods=['POST'])
def run_backtest():
    request_payload = request.json or {}
    symbol = request_payload.get('symbol')
    start_date = request_payload.get('start_date')
    end_date = request_payload.get('end_date')
    initial_capital = float(request_payload.get('initial_capital', 100000))
    strategy = request_payload.get('strategy', {})
    if not symbol or not start_date or not end_date:
        return jsonify({'error': 'symbol, start_date, end_date required'}), 400
    backtest_result = run_simple_backtest(symbol, start_date, end_date, initial_capital, strategy)
    return jsonify(backtest_result)
