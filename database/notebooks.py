"""Notebook and Notes CRUD Management Module."""

import sqlite3
from typing import Any, Dict, List, Optional
from database.database import get_db_connection


def create_notebook(title: str, description: str = "") -> int:
    """Creates a new Notebook workspace."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO notebooks (title, description) VALUES (?, ?)",
            (title.strip(), description.strip()),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_all_notebooks() -> List[Dict[str, Any]]:
    """Fetches all existing notebooks."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, description, created_at FROM notebooks ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [{"id": r[0], "title": r[1], "description": r[2], "created_at": r[3]} for r in rows]
    finally:
        conn.close()


def delete_notebook(notebook_id: int):
    """Deletes a notebook and all associated documents, notes, questions, and mistakes via CASCADE."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notebooks WHERE id = ?", (notebook_id,))
        conn.commit()
    finally:
        conn.close()


def save_note(notebook_id: int, title: str, content: str, note_type: str = "General") -> int:
    """Saves a written note, generated question paper, or mistake reminder into a notebook."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO notes (notebook_id, title, content, note_type) VALUES (?, ?, ?, ?)",
            (notebook_id, title, content, note_type),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_notebook_notes(notebook_id: int, note_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all notes saved inside a specific notebook."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if note_type:
            cursor.execute(
                "SELECT id, title, content, note_type, created_at FROM notes WHERE notebook_id = ? AND note_type = ? ORDER BY created_at DESC",
                (notebook_id, note_type),
            )
        else:
            cursor.execute(
                "SELECT id, title, content, note_type, created_at FROM notes WHERE notebook_id = ? ORDER BY created_at DESC",
                (notebook_id,),
            )
        rows = cursor.fetchall()
        return [{"id": r[0], "title": r[1], "content": r[2], "note_type": r[3], "created_at": r[4]} for r in rows]
    finally:
        conn.close()
