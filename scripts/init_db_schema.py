#!/usr/bin/env python3
"""
Consolidated Database Schema Management Script

This script provides comprehensive database schema management with two main functions:
1. init_schema() - Initialize all tables if they don't exist
2. reset_database() - Purge all data except users table
"""
import sqlite3
import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SchemaManager:
    """Manages database schema initialization and data purging"""

    def __init__(self, db_path=None, verbose=True):
        """Initialize schema manager with database path"""
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(base_dir, 'app', 'db', 'stock_predictions.db')
        else:
            self.db_path = db_path

        self.verbose = verbose  # Control output verbosity

        # Ensure database directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _log(self, message):
        """Print message only if verbose mode is enabled"""
        if self.verbose:
            print(message)

    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def init_schema(self):
        """
        Initialize all database tables if they don't already exist.
        This is safe to run multiple times - it won't affect existing data.
        """
        self._log(f"Initializing database schema at: {self.db_path}")
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # ========== USERS TABLE ==========
            self._log("  Creating users table...")
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

            # ========== WATCHLISTS TABLE ==========
            self._log("  Creating watchlists table...")
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

            # ========== STOCK QUOTES TABLE ==========
            self._log("  Creating stock_quotes table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT,
                    security_id TEXT UNIQUE,
                    scrip_code TEXT,
                    stock_symbol TEXT,
                    current_value REAL,
                    change REAL,
                    p_change REAL,
                    day_high REAL,
                    day_low REAL,
                    previous_close REAL,
                    previous_open REAL,
                    two_week_avg_quantity TEXT,
                    high_52week REAL,
                    low_52week REAL,
                    face_value REAL,
                    group_name TEXT,
                    industry TEXT,
                    market_cap_free_float TEXT,
                    market_cap_full TEXT,
                    total_traded_quantity TEXT,
                    total_traded_value TEXT,
                    updated_on TEXT,
                    weighted_avg_price REAL,
                    buy TEXT,
                    sell TEXT,
                    stock_status TEXT DEFAULT 'active',
                    download_attempts INTEGER DEFAULT 0,
                    last_download_attempt TEXT
                )
            ''')

            # ========== PREDICTIONS TABLE ==========
            self._log("  Creating predictions table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_symbol TEXT NOT NULL,
                    predicted_price REAL,
                    prediction_date TEXT,
                    user_id INTEGER,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')

            # ========== MODEL CONFIGURATIONS TABLE ==========
            self._log("  Creating model_configurations table...")
            cursor.execute('''
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
                )
            ''')

            # ========== STK TABLE (Stock Master Data) ==========
            self._log("  Creating STK table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS STK (
                    scrip_code TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL
                )
            ''')

            # ========== USER WATCHLIST TABLE (Alternative name) ==========
            self._log("  Creating user_watchlist table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    stock_symbol TEXT NOT NULL,
                    company_name TEXT,
                    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, stock_symbol)
                )
            ''')

            # ========== CREATE INDEXES ==========
            self._log("  Creating indexes...")
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_security_id ON stock_quotes (security_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_symbol ON stock_quotes (stock_symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_predictions_stock_symbol ON predictions (stock_symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON watchlists (user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_watchlist_user_id ON user_watchlist (user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_status ON stock_quotes (stock_status)')

            conn.commit()
            self._log("\n✓ Schema initialization completed successfully!")

            # Show table statistics
            if self.verbose:
                self._show_table_stats(cursor)

        except Exception as e:
            self._log(f"\n✗ Error initializing schema: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def reset_database(self, preserve_users=True):
        """
        Purge all data from the database (except users table by default).

        Args:
            preserve_users (bool): If True, keeps users table data intact. Default: True

        WARNING: This will delete all data from all tables except users!
        """
        print(f"Resetting database at: {self.db_path}")

        if preserve_users:
            print("  ⚠️  Users table will be preserved")
        else:
            print("  ⚠️  WARNING: ALL DATA INCLUDING USERS WILL BE DELETED!")

        # Confirmation
        response = input("\n  Are you sure you want to continue? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("  Operation cancelled.")
            return False

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            print("\n  Purging data from tables...")

            for table in tables:
                # Skip users table if preserve_users is True
                if preserve_users and table == 'users':
                    print(f"    ⊙ Skipping {table} (preserved)")
                    continue

                # Delete all data from table
                cursor.execute(f"DELETE FROM {table}")
                deleted_count = cursor.rowcount
                print(f"    ✓ Purged {deleted_count} records from {table}")

            # Reset autoincrement counters
            print("\n  Resetting autoincrement counters...")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name != 'users'") if preserve_users else cursor.execute("DELETE FROM sqlite_sequence")

            conn.commit()
            print("\n✓ Database reset completed successfully!")

            # Show table statistics after reset
            self._show_table_stats(cursor)

            return True

        except Exception as e:
            print(f"\n✗ Error resetting database: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def _show_table_stats(self, cursor):
        """Show statistics for all tables"""
        print("\n  Database Statistics:")
        print("  " + "="*60)

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"    {table_name:30} {count:>10} records")

        print("  " + "="*60)

    def load_stk_data(self, stk_json_path=None):
        """
        Load STK data from stk.json file into STK table.

        Args:
            stk_json_path (str): Path to stk.json file. If None, uses default location.
        """
        if stk_json_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            stk_json_path = os.path.join(base_dir, 'stk.json')

        if not os.path.exists(stk_json_path):
            print(f"  ⚠️  STK data file not found: {stk_json_path}")
            return False

        print(f"  Loading STK data from: {stk_json_path}")

        try:
            with open(stk_json_path, 'r', encoding='utf-8') as f:
                stk_data = json.load(f)

            conn = self.get_connection()
            cursor = conn.cursor()

            # Clear existing data
            cursor.execute("DELETE FROM STK")

            # Insert data
            insert_count = 0
            for scrip_code, company_name in stk_data.items():
                cursor.execute(
                    "INSERT INTO STK (scrip_code, company_name) VALUES (?, ?)",
                    (scrip_code, company_name)
                )
                insert_count += 1

            conn.commit()
            conn.close()

            print(f"  ✓ Loaded {insert_count} records into STK table")
            return True

        except Exception as e:
            print(f"  ✗ Error loading STK data: {e}")
            return False


def main():
    """Main function to handle command line arguments"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Database Schema Management Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Initialize schema (safe, won't affect existing data)
  python init_db_schema.py --init
  
  # Reset database (preserve users)
  python init_db_schema.py --reset
  
  # Reset database (delete everything including users)
  python init_db_schema.py --reset --no-preserve-users
  
  # Initialize schema and load STK data
  python init_db_schema.py --init --load-stk
        '''
    )

    parser.add_argument('--init', action='store_true',
                       help='Initialize database schema (safe operation)')
    parser.add_argument('--reset', action='store_true',
                       help='Reset database (purge all data)')
    parser.add_argument('--no-preserve-users', action='store_true',
                       help='Also delete users table when resetting (use with --reset)')
    parser.add_argument('--load-stk', action='store_true',
                       help='Load STK data from stk.json')
    parser.add_argument('--db-path', type=str,
                       help='Custom database path')

    args = parser.parse_args()

    # If no arguments provided, show help
    if not any([args.init, args.reset, args.load_stk]):
        parser.print_help()
        return

    # Create schema manager
    schema_manager = SchemaManager(db_path=args.db_path)

    try:
        # Initialize schema
        if args.init:
            schema_manager.init_schema()

            # Load STK data if requested
            if args.load_stk:
                print("\nLoading STK data...")
                schema_manager.load_stk_data()

        # Reset database
        if args.reset:
            preserve_users = not args.no_preserve_users
            schema_manager.reset_database(preserve_users=preserve_users)

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
