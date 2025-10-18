"""
Service for managing background worker settings
"""
import logging
from datetime import datetime
from typing import Dict, Any

from app.utils.util import get_db_connection


class WorkerSettingsService:
    """Service for managing worker enable/disable configuration"""

    BACKGROUND_WORKER = 'background_worker'
    INACTIVE_STOCK_WORKER = 'inactive_stock_worker'

    @staticmethod
    def is_worker_enabled(worker_name: str) -> bool:
        """Check if a worker is enabled in database configuration"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT enabled FROM worker_settings WHERE worker_name = ?
            """, (worker_name,))

            result = cursor.fetchone()
            if result:
                return bool(result['enabled'])

            # Default to enabled if no record exists
            return True

        except Exception as e:
            logging.error(f"Error checking worker enabled status: {e}")
            return True  # Default to enabled on error
        finally:
            conn.close()

    @staticmethod
    def set_worker_enabled(worker_name: str, enabled: bool) -> Dict[str, Any]:
        """Enable or disable a worker"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            now = datetime.now().isoformat()

            cursor.execute("""
                INSERT OR REPLACE INTO worker_settings (worker_name, enabled, updated_at)
                VALUES (?, ?, ?)
            """, (worker_name, 1 if enabled else 0, now))

            conn.commit()

            logging.info(f"Worker {worker_name} {'enabled' if enabled else 'disabled'}")

            return {
                'worker_name': worker_name,
                'enabled': enabled,
                'updated_at': now,
                'success': True
            }

        except Exception as e:
            conn.rollback()
            logging.error(f"Error setting worker enabled status: {e}")
            return {
                'worker_name': worker_name,
                'enabled': enabled,
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()

    @staticmethod
    def get_all_worker_settings() -> Dict[str, Any]:
        """Get settings for all workers"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM worker_settings")
            results = cursor.fetchall()

            settings = {}
            for row in results:
                settings[row['worker_name']] = {
                    'enabled': bool(row['enabled']),
                    'updated_at': row['updated_at']
                }

            return settings

        except Exception as e:
            logging.error(f"Error getting worker settings: {e}")
            return {}
        finally:
            conn.close()

    @staticmethod
    def initialize_defaults():
        """Initialize default worker settings if they don't exist"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            now = datetime.now().isoformat()

            # Create table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS worker_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_name TEXT NOT NULL UNIQUE,
                    enabled INTEGER DEFAULT 1,
                    updated_at TEXT
                )
            """)

            # Insert defaults
            cursor.execute("""
                INSERT OR IGNORE INTO worker_settings (worker_name, enabled, updated_at)
                VALUES (?, 1, ?)
            """, (WorkerSettingsService.BACKGROUND_WORKER, now))

            cursor.execute("""
                INSERT OR IGNORE INTO worker_settings (worker_name, enabled, updated_at)
                VALUES (?, 1, ?)
            """, (WorkerSettingsService.INACTIVE_STOCK_WORKER, now))

            conn.commit()
            logging.info("Worker settings initialized")

        except Exception as e:
            conn.rollback()
            logging.error(f"Error initializing worker settings: {e}")
        finally:
            conn.close()


# Initialize defaults when module is imported
try:
    WorkerSettingsService.initialize_defaults()
except Exception as e:
    logging.warning(f"Could not initialize worker settings on import: {e}")
