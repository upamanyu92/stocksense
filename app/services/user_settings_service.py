"""
User settings and onboarding service - manages user preferences,
onboarding flow, and first-run configuration.
"""
import logging
from typing import Dict, Any, Optional

from app.db.session_manager import get_session_manager

logger = logging.getLogger(__name__)

ONBOARDING_STEPS = ['welcome', 'model_setup', 'portfolio', 'watchlist', 'complete']


class UserSettingsService:
    """Manages user settings and onboarding state."""

    @staticmethod
    def ensure_table():
        """Create user_settings table if it doesn't exist."""
        db = get_session_manager()
        db.execute(
            '''CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                default_exchange TEXT DEFAULT 'NSE',
                currency TEXT DEFAULT 'INR',
                theme TEXT DEFAULT 'dark',
                onboarding_completed INTEGER DEFAULT 0,
                onboarding_step TEXT DEFAULT 'welcome',
                default_llm TEXT DEFAULT 'ollama',
                notifications_enabled INTEGER DEFAULT 1,
                email_digest_enabled INTEGER DEFAULT 0,
                risk_tolerance TEXT DEFAULT 'moderate',
                investment_horizon TEXT DEFAULT 'medium',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )''',
            commit=True,
        )

    @staticmethod
    def get_settings(user_id: int) -> Dict[str, Any]:
        """Get user settings, creating defaults if they don't exist."""
        db = get_session_manager()
        row = db.fetch_one(
            'SELECT * FROM user_settings WHERE user_id = ?',
            (user_id,),
        )

        if not row:
            # Create default settings
            db.insert(
                'INSERT INTO user_settings (user_id) VALUES (?)',
                (user_id,),
            )
            row = db.fetch_one(
                'SELECT * FROM user_settings WHERE user_id = ?',
                (user_id,),
            )

        return dict(row) if row else {
            'user_id': user_id,
            'default_exchange': 'NSE',
            'currency': 'INR',
            'theme': 'dark',
            'onboarding_completed': 0,
            'onboarding_step': 'welcome',
            'default_llm': 'ollama',
            'notifications_enabled': 1,
            'email_digest_enabled': 0,
            'risk_tolerance': 'moderate',
            'investment_horizon': 'medium',
        }

    @staticmethod
    def update_settings(user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user settings."""
        db = get_session_manager()

        # Ensure settings row exists
        UserSettingsService.get_settings(user_id)

        allowed_fields = {
            'default_exchange', 'currency', 'theme', 'default_llm',
            'notifications_enabled', 'email_digest_enabled',
            'risk_tolerance', 'investment_horizon',
        }

        set_clauses = []
        params = []
        for key, value in updates.items():
            if key in allowed_fields:
                set_clauses.append(f'{key} = ?')
                params.append(value)

        if not set_clauses:
            return False

        set_clauses.append("updated_at = datetime('now')")
        params.append(user_id)

        # Fields are from a fixed allowlist, safe from injection
        query = f"UPDATE user_settings SET {', '.join(set_clauses)} WHERE user_id = ?"  # nosec B608
        return db.update(query, tuple(params))

    # ------------------------------------------------------------------ #
    #  Onboarding
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_onboarding_status(user_id: int) -> Dict[str, Any]:
        """Get the current onboarding state."""
        settings = UserSettingsService.get_settings(user_id)

        current_step = settings.get('onboarding_step', 'welcome')
        completed = bool(settings.get('onboarding_completed', 0))

        step_index = ONBOARDING_STEPS.index(current_step) if current_step in ONBOARDING_STEPS else 0
        progress = (step_index / (len(ONBOARDING_STEPS) - 1)) * 100 if not completed else 100

        return {
            'completed': completed,
            'current_step': current_step,
            'progress': round(progress, 1),
            'steps': ONBOARDING_STEPS,
            'step_index': step_index,
        }

    @staticmethod
    def advance_onboarding(user_id: int, step: str = None) -> Dict[str, Any]:
        """Advance to the next onboarding step or a specific step."""
        db = get_session_manager()
        settings = UserSettingsService.get_settings(user_id)

        current_step = settings.get('onboarding_step', 'welcome')

        if step and step in ONBOARDING_STEPS:
            next_step = step
        else:
            current_idx = ONBOARDING_STEPS.index(current_step) if current_step in ONBOARDING_STEPS else 0
            next_idx = min(current_idx + 1, len(ONBOARDING_STEPS) - 1)
            next_step = ONBOARDING_STEPS[next_idx]

        completed = 1 if next_step == 'complete' else 0

        db.update(
            '''UPDATE user_settings
               SET onboarding_step = ?, onboarding_completed = ?, updated_at = datetime('now')
               WHERE user_id = ?''',
            (next_step, completed, user_id),
        )

        return UserSettingsService.get_onboarding_status(user_id)

    @staticmethod
    def skip_onboarding(user_id: int) -> bool:
        """Skip the entire onboarding process."""
        db = get_session_manager()
        UserSettingsService.get_settings(user_id)  # Ensure row exists
        return db.update(
            '''UPDATE user_settings
               SET onboarding_completed = 1, onboarding_step = 'complete',
                   updated_at = datetime('now')
               WHERE user_id = ?''',
            (user_id,),
        )
