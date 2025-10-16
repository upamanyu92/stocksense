"""
Script to clear all user details and all watchlists from the database.
"""
import sqlite3
import os
import logging

DB_PATH = os.path.join(os.path.dirname(__file__), '../app/db/stock_predictions.db')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clear_all():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Clear all user watchlists
        cursor.execute('DELETE FROM user_watchlist')
        logging.info('Cleared all entries from user_watchlist table.')
        # Clear all watchlists (if used)
        cursor.execute('DELETE FROM watchlists')
        logging.info('Cleared all entries from watchlists table.')
        # Clear all users
        cursor.execute('DELETE FROM users')
        logging.info('Cleared all entries from users table.')
        conn.commit()
        logging.info('All user and watchlist data cleared successfully.')
    except Exception as e:
        conn.rollback()
        logging.error(f'Error clearing tables: {e}')
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    clear_all()

