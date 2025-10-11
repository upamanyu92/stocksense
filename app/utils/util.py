import sqlite3
from typing import Optional
import os
from app.config import Config

class SQLiteConnectionPool:
    def __init__(self, db_path: str = None, pool_size: int = 5):
        self._db_path = db_path or Config.DB_PATH
        self._pool_size = pool_size
        self._connections = []
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        for _ in range(self._pool_size):
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            self._connections.append(conn)

    def get_connection(self) -> sqlite3.Connection:
        if not self._connections:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            return conn
        return self._connections.pop()

    def return_connection(self, conn: sqlite3.Connection) -> None:
        if len(self._connections) < self._pool_size:
            self._connections.append(conn)
        else:
            conn.close()
        return conn

def predict_algo(stock_data: Optional[dict], stock_symbol: str) -> float:
    if stock_data is None or stock_data.empty:
        raise ValueError("No data available for prediction")

    # For now, return a simple moving average as prediction
    last_close = stock_data['Close'].iloc[-1] if len(stock_data) > 0 else 0
    return float(last_close)
