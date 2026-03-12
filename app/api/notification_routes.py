from flask import Blueprint, jsonify, request
from app.db.services.alert_service import list_notifications, mark_notification_sent

notification_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

@notification_bp.route('/', methods=['GET'])
def api_list_notifications():
    sent = request.args.get('sent')
    if sent is None:
        notifs = list_notifications()
    else:
        try:
            sent_int = int(sent)
        except Exception:
            sent_int = None
        notifs = list_notifications(sent_int)
    return jsonify({'notifications': notifs})

@notification_bp.route('/<int:notification_id>/mark_sent', methods=['POST'])
def api_mark_sent(notification_id):
    mark_notification_sent(notification_id)
    return jsonify({'status': 'ok', 'notification_id': notification_id})
