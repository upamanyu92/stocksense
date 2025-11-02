"""
Unified database schema initialization for StockSense.
This module creates all required tables when the application starts.
"""
import sqlite3
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_db_path():
    """Get the database path"""
    # Use pathlib for more robust path resolution
    base_dir = Path(__file__).parent.parent.parent
    db_path = base_dir / 'app' / 'db' / 'stock_predictions.db'
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)


def initialize_schema():
    """
    Initialize all database tables and indexes.
    This function is idempotent - it can be called multiple times safely.
    """
    db_path = get_db_path()
    logger.info(f"Initializing database schema at {db_path}")
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create predictions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT,
                security_id TEXT UNIQUE,
                current_price REAL,
                predicted_price REAL,
                prediction_date TEXT,
                stock_status TEXT DEFAULT 'active'
            )
        ''')
        
        # Create stock_quotes table
        cursor.execute('''
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
                sell_5_price REAL,
                stock_status TEXT DEFAULT 'active',
                download_attempts INTEGER DEFAULT 0,
                last_download_attempt TEXT
            )
        ''')
        
        # Create users table for authentication
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                is_admin INTEGER DEFAULT 0
            )
        ''')
        
        # Create watchlists table for user-specific stock lists
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
        
        # Create model_configurations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_configurations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                model_type TEXT NOT NULL,
                num_heads INTEGER NOT NULL DEFAULT 4,
                ff_dim INTEGER NOT NULL DEFAULT 64,
                dropout_rate REAL NOT NULL DEFAULT 0.2,
                learning_rate REAL NOT NULL DEFAULT 0.001,
                batch_size INTEGER NOT NULL DEFAULT 32,
                epochs INTEGER NOT NULL DEFAULT 100,
                sequence_length INTEGER NOT NULL DEFAULT 60,
                early_stopping_patience INTEGER NOT NULL DEFAULT 10,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                UNIQUE(symbol, model_type)
            )
        ''')
        
        # Create chat_conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                context TEXT,
                sentiment TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # Create chat_user_preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                preferred_stocks TEXT,
                interaction_style TEXT,
                topics_of_interest TEXT,
                learning_data TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # Create chat_agent_learning table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_agent_learning (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                context_type TEXT NOT NULL,
                question_pattern TEXT NOT NULL,
                response_template TEXT NOT NULL,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                last_used TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Create indexes for better query performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_security_id ON stock_quotes (security_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_predictions_security_id ON predictions (security_id)')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_model_configs_symbol 
            ON model_configurations(symbol, model_type)
        ''')
        
        conn.commit()
        logger.info("Database schema initialized successfully")
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error initializing database schema: {e}", exc_info=True)
        raise
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    # Allow running this script directly for testing
    logging.basicConfig(level=logging.INFO)
    initialize_schema()
