import sqlite3
import os

db_path = os.path.join('app', 'db', 'stock_predictions.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- stock_quotes columns ---")
try:
    cursor.execute("PRAGMA table_info(stock_quotes)")
    columns = cursor.fetchall()
    for col in columns:
        print(col[1])
except Exception as e:
    print(e)

conn.close()
