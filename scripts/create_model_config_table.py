import os
import sqlite3
from pathlib import Path

def create_model_config_table():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(BASE_DIR, 'app', 'db', 'stock_predictions.db')

    # SQL to create model configurations table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS model_configurations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        model_type TEXT NOT NULL,
        num_heads INTEGER NOT NULL DEFAULT 4,
        ff_dim INTEGER NOT NULL DEFAULT 64,
        dropout_rate REAL NOT NULL DEFAULT 0.2,
        learning_rate REAL NOT NULL DEFAULT 0.001,
        batch_size INTEGER NOT NULL DEFAULT 32,
        epochs INTEGER NOT NULL DEFAULT 100,
        sequence_length INTEGER NOT NULL DEFAULT 60,
        early_stopping_patience INTEGER NOT NULL DEFAULT 10,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL,
        UNIQUE(symbol, model_type)
    );
    """

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create the table
        cursor.execute(create_table_sql)

        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_model_configs_symbol 
            ON model_configurations(symbol, model_type)
        """)

        conn.commit()
        print("Model configurations table created successfully")

    except Exception as e:
        print(f"Error creating table: {str(e)}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    create_model_config_table()
