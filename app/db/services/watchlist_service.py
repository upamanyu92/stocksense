"""
Watchlist database service for managing watchlists table operations
"""
from typing import Optional, List
from datetime import datetime
from app.db.session_manager import get_session_manager
from app.db.data_models import Watchlist


class WatchlistDBService:
    """Service for managing watchlists table operations"""
    
    @staticmethod
    def create(watchlist: Watchlist) -> Optional[int]:
        """Create a new watchlist entry"""
        db = get_session_manager()

        try:
            return db.insert('''
                INSERT INTO watchlists (user_id, stock_symbol, company_name, added_at, display_order)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                watchlist.user_id,
                watchlist.stock_symbol,
                watchlist.company_name,
                watchlist.added_at or datetime.now().isoformat(),
                watchlist.display_order
            ))
        except Exception as e:
            print(f"Error creating watchlist entry: {e}")
            return None

    @staticmethod
    def add(user_id: int, stock_symbol: str, company_name: str = None) -> bool:
        """Add stock to watchlist"""
        db = get_session_manager()

        try:
            return db.update('''
                INSERT INTO watchlists (user_id, stock_symbol, company_name, added_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, stock_symbol, company_name, datetime.now().isoformat()))
        except Exception as e:
            print(f"Error adding to watchlist: {e}")
            return False

    @staticmethod
    def get_by_user(user_id: int) -> List[Watchlist]:
        """Get all watchlist entries for a user"""
        db = get_session_manager()
        rows = db.fetch_all('''
            SELECT * FROM watchlists 
            WHERE user_id = ? 
            ORDER BY display_order, added_at DESC
        ''', (user_id,))
        return [Watchlist(**row) for row in rows]

    @staticmethod
    def remove(user_id: int, stock_symbol: str) -> bool:
        """Remove stock from watchlist"""
        db = get_session_manager()

        try:
            return db.delete('''
                DELETE FROM watchlists 
                WHERE user_id = ? AND stock_symbol = ?
            ''', (user_id, stock_symbol))
        except Exception as e:
            print(f"Error removing from watchlist: {e}")
            return False

    @staticmethod
    def exists(user_id: int, stock_symbol: str) -> bool:
        """Check if stock exists in user's watchlist"""
        db = get_session_manager()
        row = db.fetch_one('''
            SELECT COUNT(*) as count FROM watchlists 
            WHERE user_id = ? AND stock_symbol = ?
        ''', (user_id, stock_symbol))
        return row['count'] > 0 if row else False

    @staticmethod
    def clear(user_id: int) -> bool:
        """Clear all entries from user's watchlist"""
        db = get_session_manager()

        try:
            return db.delete('DELETE FROM watchlists WHERE user_id = ?', (user_id,))
        except Exception as e:
            print(f"Error clearing watchlist: {e}")
            return False

    @staticmethod
    def update_display_order(watchlist_id: int, display_order: int) -> bool:
        """Update display order of a watchlist entry"""
        db = get_session_manager()

        try:
            return db.update('''
                UPDATE watchlists SET display_order = ? WHERE id = ?
            ''', (display_order, watchlist_id))
        except Exception as e:
            print(f"Error updating display order: {e}")
            return False

