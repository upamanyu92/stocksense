"""
User database service for managing users table operations
"""
from typing import Optional, List
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app.db.session_manager import get_session_manager
from app.db.data_models import User as UserData


class UserService:
    """Service for managing users table operations"""
    
    @staticmethod
    def create(username: str, password: str, email: str = None) -> Optional[int]:
        """Create a new user"""
        db = get_session_manager()
        password_hash = generate_password_hash(password)
        
        try:
            return db.insert('''
                INSERT INTO users (username, password_hash, email, created_at)
                VALUES (?, ?, ?, ?)
            ''', (username, password_hash, email, datetime.now().isoformat()))
        except Exception as e:
            print(f"Error creating user: {e}")
            return None

    @staticmethod
    def create_admin(username: str, password: str, email: str = None) -> Optional[int]:
        """Create a new admin user"""
        db = get_session_manager()
        password_hash = generate_password_hash(password)

        try:
            return db.insert('''
                INSERT INTO users (username, password_hash, email, is_admin, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, password_hash, email, 1, datetime.now().isoformat()))
        except Exception as e:
            print(f"Error creating admin user: {e}")
            return None

    @staticmethod
    def get_by_id(user_id: int) -> Optional[UserData]:
        """Get user by ID"""
        db = get_session_manager()
        row = db.fetch_one('SELECT * FROM users WHERE id = ?', (user_id,))

        if row:
            return UserData(**row)
        return None
    
    @staticmethod
    def get_by_username(username: str) -> Optional[UserData]:
        """Get user by username"""
        db = get_session_manager()
        row = db.fetch_one('SELECT * FROM users WHERE username = ?', (username,))

        if row:
            return UserData(**row)
        return None
    
    @staticmethod
    def verify_password(username: str, password: str) -> bool:
        """Verify user password"""
        db = get_session_manager()
        row = db.fetch_one('SELECT password_hash FROM users WHERE username = ?', (username,))

        if row:
            return check_password_hash(row['password_hash'], password)
        return False
    
    @staticmethod
    def update(user_id: int, **kwargs) -> bool:
        """Update user fields"""
        db = get_session_manager()

        valid_fields = ['username', 'email', 'is_active']
        update_fields = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if not update_fields:
            return False
        
        set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
        values = list(update_fields.values()) + [user_id]
        
        try:
            return db.update(f'UPDATE users SET {set_clause} WHERE id = ?', tuple(values))  # nosec B608
        except Exception as e:
            print(f"Error updating user: {e}")
            return False

    @staticmethod
    def delete(user_id: int) -> bool:
        """Delete a user"""
        db = get_session_manager()

        try:
            return db.delete('DELETE FROM users WHERE id = ?', (user_id,))
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

    @staticmethod
    def get_all() -> List[UserData]:
        """Get all users"""
        db = get_session_manager()
        rows = db.fetch_all('SELECT * FROM users')
        return [UserData(**row) for row in rows]

