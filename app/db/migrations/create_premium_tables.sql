-- Premium Dashboard Tables Migration
-- Creates tables for trades tracking, user gamification, AI insights, and portfolio holdings

-- Trades/Activity tracking
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    stock_symbol TEXT NOT NULL,
    company_name TEXT,
    trade_type TEXT NOT NULL,  -- 'BUY' or 'SELL'
    quantity INTEGER NOT NULL DEFAULT 0,
    price REAL NOT NULL DEFAULT 0.0,
    total_value REAL NOT NULL DEFAULT 0.0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- User gamification levels
CREATE TABLE IF NOT EXISTS user_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    level_name TEXT DEFAULT 'Smart Investor',
    xp_points INTEGER DEFAULT 0,
    predictions_made INTEGER DEFAULT 0,
    successful_predictions INTEGER DEFAULT 0,
    streak_days INTEGER DEFAULT 0,
    badges TEXT DEFAULT '[]',
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- AI Insights feed
CREATE TABLE IF NOT EXISTS ai_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_symbol TEXT,
    insight_type TEXT NOT NULL,  -- 'buy_signal', 'sell_signal', 'trend', 'anomaly', 'sentiment'
    message TEXT NOT NULL,
    confidence REAL DEFAULT 0.0,
    source TEXT DEFAULT 'AI Engine',
    is_read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Portfolio holdings
CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    stock_symbol TEXT NOT NULL,
    company_name TEXT,
    quantity INTEGER NOT NULL DEFAULT 0,
    avg_buy_price REAL NOT NULL DEFAULT 0.0,
    current_value REAL DEFAULT 0.0,
    invested_value REAL DEFAULT 0.0,
    pnl REAL DEFAULT 0.0,
    pnl_percent REAL DEFAULT 0.0,
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id)
);
