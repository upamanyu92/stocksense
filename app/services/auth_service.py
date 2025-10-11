"""
User authentication and watchlist management service.
"""
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.utils.util import get_db_connection
from typing import Optional, List, Dict
from datetime import datetime


class User(UserMixin):
    """User model for Flask-Login"""
    
    def __init__(self, id, username, email, active=True):
        self.id = id
        self.username = username
        self.email = email
        self._active = active
    
    @property
    def is_active(self):
        """Override Flask-Login's is_active property"""
        return self._active
    
    @staticmethod
    def get_by_id(user_id: int) -> Optional['User']:
        """Get user by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, is_active FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(row['id'], row['username'], row['email'], bool(row['is_active']))
        return None
    
    @staticmethod
    def get_by_username(username: str) -> Optional['User']:
        """Get user by username"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, is_active FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(row['id'], row['username'], row['email'], bool(row['is_active']))
        return None
    
    @staticmethod
    def create_user(username: str, password: str, email: str = None) -> Optional['User']:
        """Create a new user"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        password_hash = generate_password_hash(password)
        
        try:
            cursor.execute('''
                INSERT INTO users (username, password_hash, email, created_at)
                VALUES (?, ?, ?, ?)
            ''', (username, password_hash, email, datetime.now().isoformat()))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return User.get_by_id(user_id)
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Error creating user: {e}")
            return None
    
    @staticmethod
    def verify_password(username: str, password: str) -> bool:
        """Verify user password"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return check_password_hash(row['password_hash'], password)
        return False


class WatchlistService:
    """Service for managing user watchlists"""
    
    @staticmethod
    def add_to_watchlist(user_id: int, stock_symbol: str, company_name: str = None) -> bool:
        """Add stock to user's watchlist"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO watchlists (user_id, stock_symbol, company_name, added_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, stock_symbol, company_name, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Error adding to watchlist: {e}")
            return False
    
    @staticmethod
    def remove_from_watchlist(user_id: int, stock_symbol: str) -> bool:
        """Remove stock from user's watchlist"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM watchlists WHERE user_id = ? AND stock_symbol = ?',
                          (user_id, stock_symbol))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Error removing from watchlist: {e}")
            return False
    
    @staticmethod
    def get_watchlist(user_id: int) -> List[Dict]:
        """Get user's watchlist with current stock data"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
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
            LEFT JOIN predictions p ON w.stock_symbol = p.security_id
            WHERE w.user_id = ?
            ORDER BY w.display_order, w.added_at DESC
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    @staticmethod
    def update_display_order(user_id: int, stock_symbol: str, order: int) -> bool:
        """Update display order for a stock in watchlist"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE watchlists 
                SET display_order = ?
                WHERE user_id = ? AND stock_symbol = ?
            ''', (order, user_id, stock_symbol))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Error updating display order: {e}")
            return False
