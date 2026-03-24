"""
Centralized database session manager for handling all database operations.
Provides thread-safe database access with connection pooling and proper transaction handling.
"""
import sqlite3
import threading
import time
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from queue import Queue, Empty
from app.config_settings import Config

logger = logging.getLogger(__name__)


class DatabaseSessionManager:
    """
    Centralized database session manager for handling all database operations.
    Features:
    - Connection pooling
    - Thread-safe operations
    - Automatic retry on database locks
    - Proper transaction handling
    - Context manager support
    """

    def __init__(self, db_path: str = None, pool_size: int = 10, timeout: float = 30.0, retry_count: int = 3):
        self._db_path = db_path or Config.DB_PATH
        self._pool_size = pool_size
        self._timeout = timeout
        self._retry_count = retry_count
        self._connection_pool: Queue = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._write_lock = threading.Lock()  # Additional lock for write operations
        self._initialized = False
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize the connection pool"""
        Config.ensure_directories()
        for _ in range(self._pool_size):
            try:
                conn = sqlite3.connect(self._db_path, timeout=self._timeout, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                # Enable WAL mode for better concurrency
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                self._connection_pool.put(conn)
            except Exception as e:
                logger.error(f"Failed to initialize connection in pool: {e}")
        self._initialized = True

    def get_connection(self, timeout: Optional[float] = None) -> sqlite3.Connection:
        """
        Get a connection from the pool.

        Args:
            timeout: Optional timeout in seconds. Uses class default if not provided.

        Returns:
            sqlite3.Connection: A database connection
        """
        timeout = timeout or self._timeout
        try:
            conn = self._connection_pool.get(timeout=timeout)
            return conn
        except Empty:
            # Create a new connection if pool is exhausted
            try:
                conn = sqlite3.connect(self._db_path, timeout=self._timeout, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                return conn
            except Exception as e:
                logger.error(f"Failed to create new connection: {e}")
                raise

    def release_connection(self, conn: sqlite3.Connection):
        """
        Return a connection to the pool.

        Args:
            conn: The connection to return
        """
        if conn:
            try:
                # Close any open transactions
                try:
                    conn.rollback()
                except Exception:
                    pass  # nosec B110 – best-effort rollback during connection return; errors are non-fatal
                self._connection_pool.put(conn, timeout=5)
            except Exception as e:
                logger.error(f"Failed to return connection to pool: {e}")
                try:
                    conn.close()
                except Exception:
                    pass  # nosec B110 – best-effort close; nothing more we can do at this point

    @contextmanager
    def get_session(self, timeout: Optional[float] = None):
        """
        Context manager for database sessions.
        Automatically handles connection retrieval and release.

        Args:
            timeout: Optional timeout in seconds

        Yields:
            sqlite3.Connection: A database connection

        Example:
            with db_session_manager.get_session() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM stocks")
        """
        conn = self.get_connection(timeout)
        try:
            yield conn
        finally:
            self.release_connection(conn)

    def execute(self, query: str, args: tuple = (), commit: bool = False,
                timeout: Optional[float] = None, fetch: str = None) -> Any:
        """
        Execute a query with automatic retry on database lock.

        Args:
            query: SQL query string
            args: Query parameters
            commit: Whether to commit after execution
            timeout: Optional timeout in seconds
            fetch: 'one', 'all', or None for no fetch

        Returns:
            Query result based on fetch parameter
        """
        for attempt in range(self._retry_count):
            try:
                with self.get_session(timeout) as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, args)

                    if commit:
                        conn.commit()

                    if fetch == 'one':
                        return cursor.fetchone()
                    elif fetch == 'all':
                        return cursor.fetchall()
                    else:
                        return cursor.lastrowid if commit else None
            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e) and attempt < self._retry_count - 1:
                    wait_time = 0.1 * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Database locked, retrying in {wait_time}s (attempt {attempt + 1}/{self._retry_count})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Database error on query: {query}: {e}")
                    raise
            except Exception as e:
                logger.error(f"Error executing query: {query}: {e}")
                raise

        raise RuntimeError(f"Failed to execute query after {self._retry_count} attempts")

    def fetch_one(self, query: str, args: tuple = ()) -> Optional[Dict[str, Any]]:
        """
        Fetch a single row as dictionary.

        Args:
            query: SQL query string
            args: Query parameters

        Returns:
            Dictionary of row data or None
        """
        try:
            row = self.execute(query, args, fetch='one')
            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Error in fetch_one: {e}")
            return None

    def fetch_all(self, query: str, args: tuple = ()) -> List[Dict[str, Any]]:
        """
        Fetch all rows as list of dictionaries.

        Args:
            query: SQL query string
            args: Query parameters

        Returns:
            List of dictionaries
        """
        try:
            rows = self.execute(query, args, fetch='all')
            if rows:
                return [dict(row) for row in rows]
            return []
        except Exception as e:
            logger.error(f"Error in fetch_all: {e}")
            return []

    def insert(self, query: str, args: tuple = ()) -> Optional[int]:
        """
        Insert a row and return the last row ID.

        Args:
            query: SQL insert query
            args: Query parameters

        Returns:
            Last row ID or None on error
        """
        try:
            return self.execute(query, args, commit=True)
        except Exception as e:
            logger.error(f"Error in insert: {e}")
            return None

    def update(self, query: str, args: tuple = ()) -> bool:
        """
        Update rows.

        Args:
            query: SQL update query
            args: Query parameters

        Returns:
            True if successful, False otherwise
        """
        try:
            self.execute(query, args, commit=True)
            return True
        except Exception as e:
            logger.error(f"Error in update: {e}")
            return False

    def delete(self, query: str, args: tuple = ()) -> bool:
        """
        Delete rows.

        Args:
            query: SQL delete query
            args: Query parameters

        Returns:
            True if successful, False otherwise
        """
        try:
            self.execute(query, args, commit=True)
            return True
        except Exception as e:
            logger.error(f"Error in delete: {e}")
            return False

    def execute_transaction(self, operations: List[tuple]) -> bool:
        """
        Execute multiple operations in a single transaction.

        Args:
            operations: List of (query, args, operation_type) tuples
                       operation_type: 'insert', 'update', 'delete', 'select'

        Returns:
            True if all operations succeed, False otherwise

        Example:
            operations = [
                ("INSERT INTO table VALUES (?, ?)", (val1, val2), 'insert'),
                ("UPDATE table SET col = ? WHERE id = ?", (val3, id), 'update')
            ]
            db.execute_transaction(operations)
        """
        with self._write_lock:  # Ensure only one transaction at a time
            conn = self.get_connection()
            try:
                conn.execute("BEGIN IMMEDIATE")
                cursor = conn.cursor()

                for query, args, op_type in operations:
                    cursor.execute(query, args)

                conn.commit()
                return True
            except sqlite3.OperationalError as e:
                conn.rollback()
                if 'database is locked' in str(e):
                    logger.warning(f"Database locked during transaction, retrying...")
                    time.sleep(0.2)
                    return self.execute_transaction(operations)  # Retry
                else:
                    logger.error(f"Error in transaction: {e}")
                    raise
            except Exception as e:
                conn.rollback()
                logger.error(f"Error in transaction: {e}")
                raise
            finally:
                self.release_connection(conn)

    def close_all(self):
        """Close all connections in the pool"""
        while not self._connection_pool.empty():
            try:
                conn = self._connection_pool.get_nowait()
                conn.close()
            except Empty:
                break
            except Exception as e:
                logger.error(f"Error closing connection: {e}")


# Global session manager instance
_session_manager: Optional[DatabaseSessionManager] = None
_manager_lock = threading.Lock()


def get_session_manager() -> DatabaseSessionManager:
    """
    Get the global database session manager instance (singleton).

    Returns:
        DatabaseSessionManager: The global session manager
    """
    global _session_manager
    if _session_manager is None:
        with _manager_lock:
            if _session_manager is None:
                _session_manager = DatabaseSessionManager()
    return _session_manager


# Convenience functions
def get_db_session():
    """Get a database session context manager"""
    return get_session_manager().get_session()


def execute_query(query: str, args: tuple = (), commit: bool = False, fetch: str = None) -> Any:
    """Execute a query through the session manager"""
    return get_session_manager().execute(query, args, commit, fetch=fetch)


def fetch_one(query: str, args: tuple = ()) -> Optional[Dict[str, Any]]:
    """Fetch a single row through the session manager"""
    return get_session_manager().fetch_one(query, args)


def fetch_all(query: str, args: tuple = ()) -> List[Dict[str, Any]]:
    """Fetch all rows through the session manager"""
    return get_session_manager().fetch_all(query, args)


def insert(query: str, args: tuple = ()) -> Optional[int]:
    """Insert a row through the session manager"""
    return get_session_manager().insert(query, args)


def update(query: str, args: tuple = ()) -> bool:
    """Update rows through the session manager"""
    return get_session_manager().update(query, args)


def delete(query: str, args: tuple = ()) -> bool:
    """Delete rows through the session manager"""
    return get_session_manager().delete(query, args)


def execute_transaction(operations: List[tuple]) -> bool:
    """Execute a transaction through the session manager"""
    return get_session_manager().execute_transaction(operations)


