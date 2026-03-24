from app.db.db_executor import execute_query, fetch_one
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SystemSettingsService:
    @staticmethod
    def get_setting(key: str, default_value: str = None) -> Optional[str]:
        try:
            row = fetch_one("SELECT value FROM system_settings WHERE key = ?", (key,))
            if row:
                return row['value']
            return default_value
        except Exception as e:
            logger.error(f"Error fetching system setting {key}: {e}")
            return default_value

    @staticmethod
    def update_setting(key: str, value: str, description: str = None) -> bool:
        try:
            # Upsert
            query = """
                INSERT INTO system_settings (key, value, description, updated_at) 
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET 
                    value = excluded.value,
                    description = COALESCE(excluded.description, system_settings.description),
                    updated_at = CURRENT_TIMESTAMP
            """
            execute_query(query, (key, value, description))
            return True
        except Exception as e:
            logger.error(f"Error updating system setting {key}: {e}")
            return False

