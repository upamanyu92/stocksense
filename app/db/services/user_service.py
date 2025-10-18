"""
User database service for managing users table operations
"""
from typing import Optional, List
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app.utils.util import get_db_connection
from app.db.data_models import User as UserData


class UserService:
    """Service for managing users table operations"""
    
    @staticmethod
    def create(username: str, password: str, email: str = None) -> Optional[int]:
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
            return user_id
        except Exception as e:
            conn.rollback()
            print(f"Error creating user: {e}")
            return None
        finally:
            conn.close()
    
    @staticmethod
    def get_by_id(user_id: int) -> Optional[UserData]:
        """Get user by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return UserData(**dict(row))
        return None
    
    @staticmethod
    def get_by_username(username: str) -> Optional[UserData]:
        """Get user by username"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return UserData(**dict(row))
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
    
    @staticmethod
    def update(user_id: int, **kwargs) -> bool:
        """Update user fields"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        valid_fields = ['username', 'email', 'is_active']
        update_fields = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if not update_fields:
            return False
        
        set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
        values = list(update_fields.values()) + [user_id]
        
        try:
            cursor.execute(f'UPDATE users SET {set_clause} WHERE id = ?', values)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error updating user: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def delete(user_id: int) -> bool:
        """Delete a user"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error deleting user: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def get_all() -> List[UserData]:
        """Get all users"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users')
        rows = cursor.fetchall()
        conn.close()
        return [UserData(**dict(row)) for row in rows]
