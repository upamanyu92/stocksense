from typing import Optional, Dict, Any, List
from app.db.services.alert_service import create_alert as db_create_alert, list_alerts as db_list_alerts, get_alert as db_get_alert, insert_notification as db_insert_notification
from app.models.ollama_model import predict_with_details
from app.db.session_manager import get_session_manager


def create_alert(symbol: str, condition_type: str, condition_value: float, min_confidence: float = 0.0, user_id: Optional[int] = None) -> int:
    return db_create_alert(symbol=symbol, condition_type=condition_type, condition_value=condition_value, min_confidence=min_confidence, user_id=user_id)


def list_alerts(symbol: Optional[str] = None):
    return db_list_alerts(symbol)


def _fallback_prediction_from_db(symbol: str) -> Optional[Dict[str, Any]]:
    """Attempt to use the latest stored prediction from the predictions table as a fallback."""
    try:
        db = get_session_manager()
        row = db.fetch_one(
            'SELECT predicted_price, prediction_date FROM predictions '
            'WHERE stock_symbol = ? ORDER BY prediction_date DESC LIMIT 1',
            (symbol,),
        )
        if row and row.get('predicted_price') is not None:
            return {
                'symbol': symbol,
                'predicted_price': float(row.get('predicted_price')),
                'confidence': 0.5,
                'decision': 'fallback',
                'reasoning': f'Fallback to stored prediction from {row.get("prediction_date")}'
            }
    except Exception:
        return None
    return None


def evaluate_alert(alert: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Evaluate a single alert using Ollama predictions, with DB fallback."""
    symbol = alert.get('symbol')
    condition_type = alert.get('condition_type')
    condition_value = float(alert.get('condition_value', 0.0))
    min_confidence = float(alert.get('min_confidence', 0.0))

    # Get latest prediction
    result = None
    try:
        result = predict_with_details(symbol)
    except Exception:
        # Try fallback to DB
        result = _fallback_prediction_from_db(symbol)
        if not result:
            return None

    # Check confidence threshold
    if float(result.get('confidence', 0.0)) < min_confidence:
        return None

    predicted_price = result.get('predicted_price')
    current_price = None
    # Try to get the latest current price from DB if available
    try:
        db = get_session_manager()
        row = db.fetch_one(
            'SELECT current_value FROM stock_quotes WHERE stock_symbol = ? OR company_name = ?',
            (symbol, symbol),
        )
        if row:
            current_price = float(row.get('current_value'))
    except Exception:
        current_price = None

    triggered = False
    message = ''

    if condition_type == 'price_above' and predicted_price and predicted_price > condition_value:
        triggered = True
        message = f"Predicted price for {symbol} is above {condition_value}: {predicted_price}"
    elif condition_type == 'price_below' and predicted_price and predicted_price < condition_value:
        triggered = True
        message = f"Predicted price for {symbol} is below {condition_value}: {predicted_price}"
    elif condition_type == 'predicted_change_above' and predicted_price and current_price:
        try:
            change = ((predicted_price - current_price) / current_price) * 100
            if change > condition_value:
                triggered = True
                message = f"Predicted change for {symbol} is {change:.2f}% which is above {condition_value}%"
        except Exception:
            triggered = False

    if triggered:
        notification_id = db_insert_notification(alert.get('id'), alert.get('user_id'), symbol, message, meta=str(result))
        return {'alert_id': alert.get('id'), 'notification_id': notification_id, 'message': message, 'result': result}

    return None


def run_alerts_evaluation():
    alerts = db_list_alerts()
    notifications = []
    for alert in alerts:
        if not alert.get('enabled', 1):
            continue
        alert_evaluation_result = evaluate_alert(alert)
        if alert_evaluation_result:
            notifications.append(alert_evaluation_result)
    return notifications
