import sqlite3
import os

def create_db():
    print("Creating database...")
    # Use local path instead of Docker container path
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(BASE_DIR, 'app', 'db', 'stock_predictions.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            security_id TEXT UNIQUE,
            current_price REAL,
            predicted_price REAL,
            prediction_date TEXT
        )''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS stock_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            current_value REAL,
            change REAL,
            p_change REAL,
            updated_on TEXT,
            security_id TEXT UNIQUE,
            scrip_code TEXT,
            group_type TEXT,
            face_value REAL,
            industry TEXT,
            previous_close REAL,
            previous_open REAL,
            day_high REAL,
            day_low REAL,
            week_52_high REAL,
            week_52_low REAL,
            weighted_avg_price REAL,
            total_traded_value TEXT,
            total_traded_quantity TEXT,
            two_week_avg_quantity TEXT,
            market_cap_full TEXT,
            market_cap_free_float TEXT,
            buy_1_quantity TEXT,
            buy_1_price REAL,
            buy_2_quantity TEXT,
            buy_2_price REAL,
            buy_3_quantity TEXT,
            buy_3_price REAL,
            buy_4_quantity TEXT,
            buy_4_price REAL,
            buy_5_quantity TEXT,
            buy_5_price REAL,
            sell_1_quantity TEXT,
            sell_1_price REAL,
            sell_2_quantity TEXT,
            sell_2_price REAL,
            sell_3_quantity TEXT,
            sell_3_price REAL,
            sell_4_quantity TEXT,
            sell_4_price REAL,
            sell_5_quantity TEXT,
            sell_5_price REAL
        )''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS user_watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            security_id TEXT NOT NULL,
            added_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')

    # Create indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_security_id ON stock_quotes (security_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_predictions_security_id ON predictions (security_id)')

    conn.commit()
    conn.close()
    print("Database created successfully!")

if __name__ == '__main__':
    create_db()