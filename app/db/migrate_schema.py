"""
Database schema migration script to add user authentication and stock status tracking.
"""
import sqlite3
import os

def migrate_database():
    """Add new tables and columns for authentication and stock status"""
    db_path = os.path.join(os.path.dirname(__file__), 'stock_predictions.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add users table for authentication
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Add watchlists table for user-specific stock lists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watchlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stock_symbol TEXT NOT NULL,
                company_name TEXT,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                display_order INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, stock_symbol)
            )
        ''')
        
        # Add user_watchlist table for background worker and prediction logic
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stock_symbol TEXT NOT NULL,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, stock_symbol)
            )
        ''')
        print("Ensured user_watchlist table exists")

        # Check if stock_status column exists in stock_quotes table
        cursor.execute("PRAGMA table_info(stock_quotes)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'stock_status' not in columns:
            cursor.execute('''
                ALTER TABLE stock_quotes ADD COLUMN stock_status TEXT DEFAULT 'active'
            ''')
            print("Added stock_status column to stock_quotes table")
        
        # Check if stock_status column exists in predictions table
        cursor.execute("PRAGMA table_info(predictions)")
        pred_columns = [column[1] for column in cursor.fetchall()]
        
        if 'stock_status' not in pred_columns:
            cursor.execute('''
                ALTER TABLE predictions ADD COLUMN stock_status TEXT DEFAULT 'active'
            ''')
            print("Added stock_status column to predictions table")
        
        # Add download_attempts and last_download_attempt columns to track failures
        if 'download_attempts' not in columns:
            cursor.execute('''
                ALTER TABLE stock_quotes ADD COLUMN download_attempts INTEGER DEFAULT 0
            ''')
            print("Added download_attempts column to stock_quotes table")
        
        if 'last_download_attempt' not in columns:
            cursor.execute('''
                ALTER TABLE stock_quotes ADD COLUMN last_download_attempt TEXT
            ''')
            print("Added last_download_attempt column to stock_quotes table")
        
        conn.commit()
        print("Database migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()
