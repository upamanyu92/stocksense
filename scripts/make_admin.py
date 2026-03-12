import sqlite3
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Config from app.config.py (not the app/config/ directory)
try:
    from app.config import Config
    DB_PATH = Config.DB_PATH
except ImportError:
    # Fallback if Config cannot be imported
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, 'app', 'db', 'stock_predictions.db')

def make_admin(username):
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if user exists
        cursor.execute("SELECT id, username, is_admin FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if user:
            print(f"User found: ID={user[0]}, Username={user[1]}, Current is_admin={user[2]}")
            cursor.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (username,))
            conn.commit()
            print(f"Successfully updated {username} to admin.")
        else:
            print(f"User '{username}' not found in the database.")
            
            # List all users to help debugging
            cursor.execute("SELECT username FROM users")
            users = cursor.fetchall()
            if users:
                print("Available users: " + ", ".join([u[0] for u in users]))
            else:
                print("No users found in the database.")
                
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    target_user = "admin"
    if len(sys.argv) > 1:
        target_user = sys.argv[1]
    make_admin(target_user)
