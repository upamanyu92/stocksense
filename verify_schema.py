import sqlite3
import os

db_path = os.path.join('app', 'db', 'stock_predictions.db')
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def check_table(table_name):
    print(f"\n--- {table_name} columns ---")
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
    except Exception as e:
        print(f"Error checking {table_name}: {e}")

check_table('predictions')
check_table('stock_quotes')

conn.close()
