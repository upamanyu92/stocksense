"""
Watchlist database service for managing watchlists table operations
"""
from typing import Optional, List
from datetime import datetime
from app.utils.util import get_db_connection
from app.db.data_models import Watchlist


class WatchlistDBService:
    """Service for managing watchlists table operations"""
    
    @staticmethod
    def create(watchlist: Watchlist) -> Optional[int]:
        """Create a new watchlist entry"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO watchlists (user_id, stock_symbol, company_name, added_at, display_order)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                watchlist.user_id,
                watchlist.stock_symbol,
                watchlist.company_name,
                watchlist.added_at or datetime.now().isoformat(),
                watchlist.display_order
            ))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            conn.rollback()
            print(f"Error creating watchlist entry: {e}")
            return None
        finally:
            conn.close()
    
    @staticmethod
    def add(user_id: int, stock_symbol: str, company_name: str = None) -> bool:
        """Add stock to watchlist"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO watchlists (user_id, stock_symbol, company_name, added_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, stock_symbol, company_name, datetime.now().isoformat()))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error adding to watchlist: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def get_by_user(user_id: int) -> List[Watchlist]:
        """Get all watchlist entries for a user"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM watchlists 
            WHERE user_id = ? 
            ORDER BY display_order, added_at DESC
        ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [Watchlist(**dict(row)) for row in rows]
    
    @staticmethod
    def remove(user_id: int, stock_symbol: str) -> bool:
        """Remove stock from watchlist"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                DELETE FROM watchlists 
                WHERE user_id = ? AND stock_symbol = ?
            ''', (user_id, stock_symbol))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error removing from watchlist: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def exists(user_id: int, stock_symbol: str) -> bool:
        """Check if stock exists in user's watchlist"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM watchlists 
            WHERE user_id = ? AND stock_symbol = ?
        ''', (user_id, stock_symbol))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    
    @staticmethod
    def clear(user_id: int) -> bool:
        """Clear all entries from user's watchlist"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM watchlists WHERE user_id = ?', (user_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error clearing watchlist: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def update_display_order(watchlist_id: int, display_order: int) -> bool:
        """Update display order of a watchlist entry"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE watchlists SET display_order = ? WHERE id = ?
            ''', (display_order, watchlist_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error updating display order: {e}")
            return False
        finally:
            conn.close()
