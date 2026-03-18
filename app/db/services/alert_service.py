from typing import List, Dict, Any, Optional
from app.db.session_manager import get_session_manager

ALERT_TABLE_SCHEMA = {
    'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
}


def create_alert(symbol: str, condition_type: str, condition_value: float, min_confidence: float = 0.0, user_id: Optional[int] = None) -> int:
    db = get_session_manager()
    sql = '''INSERT INTO alerts (user_id, symbol, condition_type, condition_value, min_confidence, enabled)
             VALUES (?, ?, ?, ?, ?, 1)'''
    db.insert(sql, (user_id, symbol, condition_type, condition_value, min_confidence))
    # Return last inserted id
    row = db.fetch_one('SELECT last_insert_rowid() AS id')
    return row['id'] if row else -1


def list_alerts(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    db = get_session_manager()
    if symbol:
        return db.fetch_all('SELECT * FROM alerts WHERE symbol = ?', (symbol,))
    return db.fetch_all('SELECT * FROM alerts')


def get_alert(alert_id: int) -> Optional[Dict[str, Any]]:
    db = get_session_manager()
    return db.fetch_one('SELECT * FROM alerts WHERE id = ?', (alert_id,))


def set_alert_enabled(alert_id: int, enabled: bool):
    db = get_session_manager()
    db.update('UPDATE alerts SET enabled = ? WHERE id = ?', (1 if enabled else 0, alert_id))


def insert_notification(alert_id: Optional[int], user_id: Optional[int], symbol: str, message: str, meta: Optional[str] = None) -> int:
    db = get_session_manager()
    sql = '''INSERT INTO notifications (alert_id, user_id, symbol, message, meta, sent) VALUES (?, ?, ?, ?, ?, 0)'''
    db.insert(sql, (alert_id, user_id, symbol, message, meta))
    row = db.fetch_one('SELECT last_insert_rowid() AS id')
    return row['id'] if row else -1


def list_notifications(sent: Optional[int] = None) -> List[Dict[str, Any]]:
    db = get_session_manager()
    if sent is None:
        return db.fetch_all('SELECT * FROM notifications ORDER BY created_at DESC')
    return db.fetch_all('SELECT * FROM notifications WHERE sent = ? ORDER BY created_at DESC', (sent,))


def mark_notification_sent(notification_id: int):
    db = get_session_manager()
    db.update('UPDATE notifications SET sent = 1 WHERE id = ?', (notification_id,))

