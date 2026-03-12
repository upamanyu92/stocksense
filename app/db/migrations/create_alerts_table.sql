-- Migration: create alerts and notifications tables

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER DEFAULT NULL,
    symbol TEXT NOT NULL,
    condition_type TEXT NOT NULL, -- e.g., price_above, price_below, predicted_change_above
    condition_value REAL NOT NULL,
    min_confidence REAL DEFAULT 0.0,
    enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alerts_symbol ON alerts(symbol);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER DEFAULT NULL,
    user_id INTEGER DEFAULT NULL,
    symbol TEXT,
    message TEXT,
    meta JSON DEFAULT NULL,
    sent INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notifications_sent ON notifications(sent);
