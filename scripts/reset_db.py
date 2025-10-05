import os
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(BASE_DIR, 'app', 'db', 'stock_predictions.db')

if os.path.exists(db_path):
    print(f"Deleting {db_path}...")
    os.remove(db_path)
else:
    print(f"{db_path} does not exist, nothing to delete.")

print("Recreating database...")
subprocess.run(['python3', 'create_db.py'], check=True)
subprocess.run(['python3', 'create_model_config_table.py'], check=True)
print("Database reset complete.")

