"""Database Connection Management and Schema Initialization."""

import logging
import sqlite3
from typing import Optional
from config import DATABASE_PATH
from database.schema import ALL_SCHEMA_STATEMENTS

logger = logging.getLogger(__name__)


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Creates and returns a SQLite database connection with row factory and foreign keys enabled."""
    target_path = db_path or str(DATABASE_PATH)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db(db_path: Optional[str] = None):
    """Executes all schema table and index creation statements on application startup."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        for statement in ALL_SCHEMA_STATEMENTS:
            cursor.execute(statement)
        conn.commit()
        logger.info("Database schema initialized successfully at '%s'.", db_path or DATABASE_PATH)


# Direct function alias for cross-module import compatibility
get_connection = get_db_connection
