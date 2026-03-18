"""
User authentication and watchlist management service.
"""
from werkzeug.security import check_password_hash
from flask_login import UserMixin
from typing import Optional, List, Dict
from datetime import datetime

from app.db.services.user_service import UserService
from app.db.services.watchlist_service import WatchlistDBService
from app.db.session_manager import get_session_manager


class User(UserMixin):
    """User model for Flask-Login"""
    
    def __init__(self, id, username, email, active=True, subscription_tier='free', subscription_expires_at=None):
        self.id = id
        self.username = username
        self.email = email
        self._active = active
        self.subscription_tier = subscription_tier
        self.subscription_expires_at = subscription_expires_at
    
    @property
    def is_active(self):
        """Override Flask-Login's is_active property"""
        return self._active
    
    @staticmethod
    def get_by_id(user_id: int) -> Optional['User']:
        """Get user by ID"""
        user_data = UserService.get_by_id(user_id)
        if user_data:
            return User(
                user_data.id, 
                user_data.username, 
                user_data.email, 
                bool(user_data.is_active),
                user_data.subscription_tier,
                user_data.subscription_expires_at
            )
        return None
    
    @staticmethod
    def get_by_username(username: str) -> Optional['User']:
        """Get user by username"""
        user_data = UserService.get_by_username(username)
        if user_data:
            return User(
                user_data.id, 
                user_data.username, 
                user_data.email, 
                bool(user_data.is_active),
                user_data.subscription_tier,
                user_data.subscription_expires_at
            )
        return None
    
    @staticmethod
    def create_user(username: str, password: str, email: str = None) -> Optional['User']:
        """Create a new user"""
        user_id = UserService.create(username, password, email)
        if user_id:
            return User.get_by_id(user_id)
        return None

    @staticmethod
    def create_admin_user(username: str, password: str, email: str = None) -> Optional['User']:
        """Create a new admin user"""
        user_id = UserService.create_admin(username, password, email)
        if user_id:
            return User.get_by_id(user_id)
        return None
    
    @staticmethod
    def verify_password(username: str, password: str) -> bool:
        """Verify user password"""
        return UserService.verify_password(username, password)

    def is_pro(self) -> bool:
        """Check if user has pro subscription"""
        if self.subscription_tier == 'pro':
            if self.subscription_expires_at:
                try:
                    expiry = datetime.fromisoformat(self.subscription_expires_at)
                    return expiry > datetime.now()
                except ValueError:
                    return False
            return True # No expiry means lifetime pro for now
        return False


class WatchlistService:
    """Service for managing user watchlists"""
    
    @staticmethod
    def add_to_watchlist(user_id: int, stock_symbol: str, company_name: str = None) -> bool:
        """Add stock to user's watchlist"""
        return WatchlistDBService.add(user_id, stock_symbol, company_name)
    
    @staticmethod
    def remove_from_watchlist(user_id: int, stock_symbol: str) -> bool:
        """Remove stock from user's watchlist"""
        return WatchlistDBService.remove(user_id, stock_symbol)
    
    @staticmethod
    def get_watchlist(user_id: int) -> List[Dict]:
        """Get user's watchlist with current stock data"""
        db = get_session_manager()

        rows = db.fetch_all('''
            SELECT 
                w.stock_symbol,
                w.company_name,
                w.added_at,
                sq.current_value as current_price,
                sq.change,
                sq.p_change,
                sq.day_high,
                sq.day_low,
                sq.stock_status,
                p.predicted_price,
                p.prediction_date
            FROM watchlists w
            LEFT JOIN stock_quotes sq ON w.stock_symbol = sq.security_id
            LEFT JOIN predictions p ON w.stock_symbol = p.stock_symbol
            WHERE w.user_id = ?
            ORDER BY w.display_order, w.added_at DESC
        ''', (user_id,))
        
        return rows

    @staticmethod
    def update_display_order(user_id: int, stock_symbol: str, order: int) -> bool:
        """Update display order for a stock in watchlist"""
        db = get_session_manager()

        try:
            return db.update('''
                UPDATE watchlists 
                SET display_order = ?
                WHERE user_id = ? AND stock_symbol = ?
            ''', (order, user_id, stock_symbol))
        except Exception as e:
            print(f"Error updating display order: {e}")
            return False
