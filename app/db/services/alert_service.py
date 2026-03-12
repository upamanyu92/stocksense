from typing import List, Dict, Any, Optional
from app.db.db_executor import execute_query, fetch_all, fetch_one

ALERT_TABLE_SCHEMA = {
    'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
}


def create_alert(symbol: str, condition_type: str, condition_value: float, min_confidence: float = 0.0, user_id: Optional[int] = None) -> int:
    sql = '''INSERT INTO alerts (user_id, symbol, condition_type, condition_value, min_confidence, enabled)
             VALUES (?, ?, ?, ?, ?, 1)'''
    execute_query(sql, (user_id, symbol, condition_type, condition_value, min_confidence), commit=True)
    # Return last inserted id
    row = fetch_one('SELECT last_insert_rowid() AS id')
    return row['id'] if row else -1


def list_alerts(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    if symbol:
        return fetch_all('SELECT * FROM alerts WHERE symbol = ?', (symbol,))
    return fetch_all('SELECT * FROM alerts')


def get_alert(alert_id: int) -> Optional[Dict[str, Any]]:
    return fetch_one('SELECT * FROM alerts WHERE id = ?', (alert_id,))


def set_alert_enabled(alert_id: int, enabled: bool):
    execute_query('UPDATE alerts SET enabled = ? WHERE id = ?', (1 if enabled else 0, alert_id), commit=True)


def insert_notification(alert_id: Optional[int], user_id: Optional[int], symbol: str, message: str, meta: Optional[str] = None) -> int:
    sql = '''INSERT INTO notifications (alert_id, user_id, symbol, message, meta, sent) VALUES (?, ?, ?, ?, ?, 0)'''
    execute_query(sql, (alert_id, user_id, symbol, message, meta), commit=True)
    row = fetch_one('SELECT last_insert_rowid() AS id')
    return row['id'] if row else -1


def list_notifications(sent: Optional[int] = None) -> List[Dict[str, Any]]:
    if sent is None:
        return fetch_all('SELECT * FROM notifications ORDER BY created_at DESC')
    return fetch_all('SELECT * FROM notifications WHERE sent = ? ORDER BY created_at DESC', (sent,))


def mark_notification_sent(notification_id: int):
    execute_query('UPDATE notifications SET sent = 1 WHERE id = ?', (notification_id,), commit=True)
