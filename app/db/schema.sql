-- User table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    created_at TEXT,
    is_active INTEGER DEFAULT 1
);

-- Watchlist table
CREATE TABLE IF NOT EXISTS watchlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    stock_symbol TEXT NOT NULL,
    company_name TEXT,
    added_at TEXT,
    display_order INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- ModelConfiguration table
CREATE TABLE IF NOT EXISTS model_configurations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    model_type TEXT DEFAULT 'transformer',
    num_heads INTEGER DEFAULT 4,
    ff_dim INTEGER DEFAULT 64,
    dropout_rate REAL DEFAULT 0.2,
    learning_rate REAL DEFAULT 0.001,
    batch_size INTEGER DEFAULT 32,
    epochs INTEGER DEFAULT 100,
    sequence_length INTEGER DEFAULT 60
);

-- StockQuotes table
CREATE TABLE IF NOT EXISTS stock_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_symbol TEXT NOT NULL,
    current_value REAL,
    change REAL,
    p_change REAL,
    day_high REAL,
    day_low REAL,
    stock_status TEXT,
    last_updated TEXT
);

-- Predictions table
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_symbol TEXT NOT NULL,
    predicted_price REAL,
    prediction_date TEXT,
    user_id INTEGER,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
