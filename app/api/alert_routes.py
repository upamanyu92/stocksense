from flask import Blueprint, request, jsonify
from app.services.alert_service import create_alert, list_alerts, run_alerts_evaluation

bp = Blueprint('alert_routes', __name__, url_prefix='/api/alerts')

@bp.route('/', methods=['POST'])
def api_create_alert():
    data = request.json or {}
    symbol = data.get('symbol')
    condition_type = data.get('condition_type')
    condition_value = float(data.get('condition_value', 0.0))
    min_confidence = float(data.get('min_confidence', 0.0))
    user_id = data.get('user_id')

    if not symbol or not condition_type:
        return jsonify({'error': 'symbol and condition_type are required'}), 400

    alert_id = create_alert(symbol, condition_type, condition_value, min_confidence, user_id)
    return jsonify({'status': 'created', 'alert_id': alert_id})

@bp.route('/', methods=['GET'])
def api_list_alerts():
    symbol = request.args.get('symbol')
    alerts = list_alerts(symbol)
    return jsonify({'alerts': alerts})

@bp.route('/evaluate', methods=['POST'])
def api_evaluate_alerts():
    # Trigger evaluation of all alerts (for testing)
    results = run_alerts_evaluation()
    return jsonify({'notifications': results})
