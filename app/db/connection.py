import sqlite3
from queue import Queue
from threading import Lock

class SQLiteConnectionPool:
    def __init__(self, db_path, pool_size=5):
        self._db_path = db_path
        self._pool_size = pool_size
        self._lock = Lock()
        self._pool = Queue(maxsize=self._pool_size)
        self._initialize_pool()

    def _initialize_pool(self):
        for _ in range(self._pool_size):
            conn = sqlite3.connect(self._db_path)
            self._pool.put(conn)

    def get_connection(self):
        with self._lock:
            if self._pool.empty():
                conn = sqlite3.connect(self._db_path)
            else:
                conn = self._pool.get()
            return conn

    def release_connection(self, conn):
        with self._lock:
            self._pool.put(conn)

    def close_all_connections(self):
        with self._lock:
            while not self._pool.empty():
                conn = self._pool.get()
                conn.close()
