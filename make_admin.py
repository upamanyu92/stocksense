from app.db.db_executor import execute_query, fetch_one

def make_admin(username):
    user = fetch_one("SELECT * FROM users WHERE username = ?", (username,))
    if user:
        print(f"User {username} found. Setting is_admin = 1...")
        execute_query("UPDATE users SET is_admin = 1 WHERE username = ?", (username,), commit=True)
        print(f"User {username} is now an admin.")
    else:
        print(f"User {username} not found.")

if __name__ == "__main__":
    make_admin("admin")
