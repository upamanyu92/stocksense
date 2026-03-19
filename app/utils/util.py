"""
Database utility helpers.

get_db_connection() is kept for backward compatibility but delegates to
the session manager's connection pool. New code should use
app.db.session_manager.get_session_manager() directly.
"""
import sqlite3


def get_db_connection() -> sqlite3.Connection:
    """Return a pooled SQLite connection with row_factory set.

    NOTE: Callers are responsible for releasing the connection back to
    the pool via ``get_session_manager().release_connection(conn)``.
    Prefer using ``get_session_manager().get_session()`` as a context
    manager for automatic cleanup.
    """
    from app.db.session_manager import get_session_manager
    return get_session_manager().get_connection()
