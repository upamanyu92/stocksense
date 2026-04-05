-- Migration: Portfolio Management & Extended Finance Tables
-- Creates tables for full portfolio management, XLSX imports, quote history,
-- user settings/onboarding, and AI portfolio analysis

-- Portfolio transactions (buy/sell history with more detail than trades)
CREATE TABLE IF NOT EXISTS portfolio_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    stock_symbol TEXT NOT NULL,
    company_name TEXT,
    transaction_type TEXT NOT NULL CHECK(transaction_type IN ('BUY', 'SELL', 'DIVIDEND', 'SPLIT', 'BONUS')),
    quantity REAL NOT NULL DEFAULT 0,
    price REAL NOT NULL DEFAULT 0.0,
    total_value REAL NOT NULL DEFAULT 0.0,
    fees REAL DEFAULT 0.0,
    notes TEXT,
    transaction_date TEXT NOT NULL,
    source TEXT DEFAULT 'manual',  -- 'manual', 'xlsx_import', 'csv_import'
    import_batch_id TEXT,          -- links to portfolio_imports.batch_id
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_user ON portfolio_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_symbol ON portfolio_transactions(stock_symbol);
CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_date ON portfolio_transactions(transaction_date);

-- Portfolio import logs (tracks XLSX/CSV imports)
CREATE TABLE IF NOT EXISTS portfolio_imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    batch_id TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL DEFAULT 'xlsx',  -- 'xlsx', 'csv'
    broker_format TEXT,                       -- 'zerodha', 'groww', 'angel', 'generic', etc.
    total_rows INTEGER DEFAULT 0,
    imported_rows INTEGER DEFAULT 0,
    skipped_rows INTEGER DEFAULT 0,
    error_rows INTEGER DEFAULT 0,
    errors TEXT,                              -- JSON array of error details
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
    created_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_imports_user ON portfolio_imports(user_id);

-- Quote history cache (stores historical price snapshots)
CREATE TABLE IF NOT EXISTS quote_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    volume INTEGER,
    adj_close REAL,
    source TEXT DEFAULT 'yfinance',
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(stock_symbol, date)
);

CREATE INDEX IF NOT EXISTS idx_quote_history_symbol ON quote_history(stock_symbol);
CREATE INDEX IF NOT EXISTS idx_quote_history_date ON quote_history(date);

-- User settings/preferences (extended beyond chat preferences)
CREATE TABLE IF NOT EXISTS user_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    default_exchange TEXT DEFAULT 'NSE',       -- 'NSE', 'BSE', 'NYSE', 'NASDAQ'
    currency TEXT DEFAULT 'INR',
    theme TEXT DEFAULT 'dark',
    onboarding_completed INTEGER DEFAULT 0,
    onboarding_step TEXT DEFAULT 'welcome',    -- 'welcome', 'model_setup', 'portfolio', 'watchlist', 'complete'
    default_llm TEXT DEFAULT 'ollama',         -- 'ollama', 'gemini', 'copilot'
    notifications_enabled INTEGER DEFAULT 1,
    email_digest_enabled INTEGER DEFAULT 0,
    risk_tolerance TEXT DEFAULT 'moderate',    -- 'conservative', 'moderate', 'aggressive'
    investment_horizon TEXT DEFAULT 'medium',  -- 'short', 'medium', 'long'
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- AI portfolio analysis results (cached analysis)
CREATE TABLE IF NOT EXISTS portfolio_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    analysis_type TEXT NOT NULL,  -- 'summary', 'risk', 'allocation', 'recommendation', 'performance'
    content TEXT NOT NULL,        -- JSON or markdown analysis content
    model_used TEXT,              -- 'ollama', 'gemini', 'copilot', 'fallback'
    confidence REAL DEFAULT 0.0,
    metadata TEXT,                -- JSON metadata
    created_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT,              -- cache expiry
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_analysis_user ON portfolio_analysis(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_analysis_type ON portfolio_analysis(analysis_type);
