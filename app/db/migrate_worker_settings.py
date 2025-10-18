"""
Migration script to add worker_settings table for background worker control
"""
import logging
from datetime import datetime

from app.utils.util import get_db_connection


def migrate_worker_settings():
    """Add worker_settings table if it doesn't exist and initialize default values"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Create worker_settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS worker_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_name TEXT NOT NULL UNIQUE,
                enabled INTEGER DEFAULT 1,
                updated_at TEXT
            )
        """)

        # Initialize default settings for both workers
        now = datetime.now().isoformat()

        # Insert default settings if they don't exist
        cursor.execute("""
            INSERT OR IGNORE INTO worker_settings (worker_name, enabled, updated_at)
            VALUES ('background_worker', 1, ?)
        """, (now,))

        cursor.execute("""
            INSERT OR IGNORE INTO worker_settings (worker_name, enabled, updated_at)
            VALUES ('inactive_stock_worker', 1, ?)
        """, (now,))

        conn.commit()
        logging.info("Worker settings table migration completed successfully")

    except Exception as e:
        conn.rollback()
        logging.error(f"Error migrating worker_settings table: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    migrate_worker_settings()
