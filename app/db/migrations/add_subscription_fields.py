import sqlite3
import os
import logging

def migrate():
    """Add subscription fields to users table"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'stock_predictions.db')
    if not os.path.exists(db_path):
        logging.error(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'subscription_tier' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN subscription_tier TEXT DEFAULT 'free'")
            logging.info("Added subscription_tier column to users table")
        
        if 'subscription_expires_at' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN subscription_expires_at TEXT")
            logging.info("Added subscription_expires_at column to users table")
            
        conn.commit()
        logging.info("Subscription fields migration completed successfully!")
    except Exception as e:
        conn.rollback()
        logging.error(f"Error during subscription migration: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    migrate()
