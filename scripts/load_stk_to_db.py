#!/usr/bin/env python3
"""
Script to load stk.json into stock_predictions.db as STK table
with columns: scrip_code and company_name
"""
import json
import sqlite3
import os
import sys

# Add parent directory to path to import app modules if needed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_stk_to_db():
    """Load stk.json data into STK table in stock_predictions.db"""

    # Define file paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    stk_json_path = os.path.join(base_dir, 'stk.json')
    db_path = os.path.join(base_dir, 'app', 'db', 'stock_predictions.db')

    print(f"Loading data from: {stk_json_path}")
    print(f"Database path: {db_path}")

    # Check if stk.json exists
    if not os.path.exists(stk_json_path):
        print(f"Error: {stk_json_path} not found!")
        return False

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found!")
        return False

    # Load stk.json
    try:
        with open(stk_json_path, 'r', encoding='utf-8') as f:
            stk_data = json.load(f)
        print(f"Loaded {len(stk_data)} records from stk.json")
    except Exception as e:
        print(f"Error loading stk.json: {e}")
        return False

    # Connect to database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create STK table (drop if exists)
        print("Creating STK table...")
        cursor.execute("DROP TABLE IF EXISTS STK")
        cursor.execute("""
            CREATE TABLE STK (
                scrip_code TEXT PRIMARY KEY,
                company_name TEXT NOT NULL
            )
        """)

        # Insert data
        print("Inserting data into STK table...")
        insert_count = 0
        for scrip_code, company_name in stk_data.items():
            cursor.execute(
                "INSERT INTO STK (scrip_code, company_name) VALUES (?, ?)",
                (scrip_code, company_name)
            )
            insert_count += 1

        # Commit changes
        conn.commit()
        print(f"Successfully inserted {insert_count} records into STK table")

        # Verify the data
        cursor.execute("SELECT COUNT(*) FROM STK")
        count = cursor.fetchone()[0]
        print(f"Verification: STK table now contains {count} records")

        # Show sample records
        cursor.execute("SELECT * FROM STK LIMIT 5")
        sample_records = cursor.fetchall()
        print("\nSample records:")
        for record in sample_records:
            print(f"  {record[0]}: {record[1]}")

        conn.close()
        print("\n✓ Successfully loaded stk.json into STK table!")
        return True

    except Exception as e:
        print(f"Error working with database: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False


if __name__ == "__main__":
    success = load_stk_to_db()
    sys.exit(0 if success else 1)

