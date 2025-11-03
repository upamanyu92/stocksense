"""
Create default admin user for testing.
Run this script once to create the default admin account.
"""
from app.services.auth_service import User

def create_default_user():
    """Create default admin user if it doesn't exist"""
    username = "admin"
    password = "admin123"
    email = "admin@stocksense.local"
    
    # Check if user already exists
    existing_user = User.get_by_username(username)
    if existing_user:
        print(f"User '{username}' already exists.")
        return
    
    # Create user
    user = User.create_admin_user(username, password, email)
    if user:
        print(f"✓ Default user created successfully!")
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        print(f"  Email: {email}")
        print(f"\nPlease change the password after first login.")
    else:
        print("✗ Failed to create default user.")

if __name__ == '__main__':
    create_default_user()
