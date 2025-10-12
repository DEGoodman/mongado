"""Database connection and initialization for Zettelkasten notes."""

import logging
import sqlite3
from pathlib import Path
from typing import Any

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Database:
    """SQLite database manager for Zettelkasten notes."""

    def __init__(self, db_path: str | Path | None = None):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file. Defaults to mongado.db in backend/
        """
        if db_path is None:
            db_path = Path(__file__).parent / "mongado.db"
        else:
            db_path = Path(db_path)

        self.db_path = db_path
        self.schema_path = Path(__file__).parent / "db_schema.sql"
        self._conn: sqlite3.Connection | None = None

        # Initialize database on creation
        self._initialize()

    def _initialize(self) -> None:
        """Initialize database schema if it doesn't exist."""
        # Check if database file exists
        db_exists = self.db_path.exists()

        if not db_exists:
            logger.info("Creating new database at %s", self.db_path)

        # Connect and run schema
        conn = self.get_connection()

        if not self.schema_path.exists():
            logger.error("Schema file not found: %s", self.schema_path)
            return

        with open(self.schema_path) as f:
            schema_sql = f.read()

        conn.executescript(schema_sql)
        conn.commit()

        if not db_exists:
            logger.info("Database initialized successfully")
        else:
            logger.debug("Database schema verified")

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection (reuse existing or create new).

        Returns:
            SQLite connection with row factory enabled
        """
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,  # Allow multi-threaded access
            )
            # Enable dict-like row access
            self._conn.row_factory = sqlite3.Row

        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.debug("Database connection closed")

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        """Execute a query and return cursor.

        Args:
            query: SQL query string
            params: Query parameters (tuple)

        Returns:
            Cursor with query results
        """
        conn = self.get_connection()
        return conn.execute(query, params)

    def executemany(self, query: str, params: list[tuple[Any, ...]]) -> sqlite3.Cursor:
        """Execute a query multiple times with different parameters.

        Args:
            query: SQL query string
            params: List of parameter tuples

        Returns:
            Cursor with query results
        """
        conn = self.get_connection()
        return conn.executemany(query, params)

    def commit(self) -> None:
        """Commit pending transactions."""
        conn = self.get_connection()
        conn.commit()

    def rollback(self) -> None:
        """Rollback pending transactions."""
        conn = self.get_connection()
        conn.rollback()

    def fetchone(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        """Execute query and fetch one result as dict.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Dict of column->value or None if no results
        """
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """Execute query and fetch all results as list of dicts.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of dicts (column->value)
        """
        cursor = self.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


# Global database instance
_db: Database | None = None


def get_database() -> Database:
    """Get global database instance (singleton).

    Returns:
        Database instance
    """
    global _db
    if _db is None:
        _db = Database()
    return _db


def close_database() -> None:
    """Close global database connection."""
    global _db
    if _db:
        _db.close()
        _db = None
