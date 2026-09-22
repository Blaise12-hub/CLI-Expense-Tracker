"""
db.py — Database operations for the CLI Expense Tracker.

Handles schema initialisation and all CRUD operations against expenses.db.
Amounts are stored as TEXT strings to preserve Decimal precision.
"""

import sqlite3
from decimal import Decimal
from pathlib import Path

DB_PATH = Path(__file__).parent / "expenses.db"


def _get_connection() -> sqlite3.Connection:
    """Open and return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # enable column-name access on rows
    return conn


def init_db() -> None:
    """Create the expenses table if it does not already exist."""
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT    NOT NULL,
                category    TEXT    NOT NULL,
                description TEXT    NOT NULL,
                amount      TEXT    NOT NULL
            )
            """
        )
        conn.commit()


def add_expense(
    date: str,
    category: str,
    description: str,
    amount: Decimal,
) -> int:
    """Insert a new expense row and return its auto-assigned ID.

    Args:
        date: ISO-8601 date string, e.g. '2026-09-22'.
        category: Expense category label, e.g. 'Food'.
        description: Free-text note about the expense.
        amount: Monetary value as a Decimal to avoid float errors.

    Returns:
        The integer row ID of the newly inserted expense.
    """
    with _get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO expenses (date, category, description, amount) VALUES (?, ?, ?, ?)",
            (date, category, description, str(amount)),
        )
        conn.commit()
        return cursor.lastrowid


def list_expenses(category: str | None = None) -> list[sqlite3.Row]:
    """Return all expenses, optionally filtered by category.

    Args:
        category: If provided, only rows matching this category are returned
                  (case-insensitive).

    Returns:
        A list of sqlite3.Row objects ordered by date ascending.
    """
    with _get_connection() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM expenses WHERE LOWER(category) = LOWER(?) ORDER BY date ASC",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM expenses ORDER BY date ASC"
            ).fetchall()
    return rows


def delete_expense(expense_id: int) -> bool:
    """Delete an expense by its ID.

    Args:
        expense_id: The integer primary key of the row to remove.

    Returns:
        True if a row was deleted, False if the ID was not found.
    """
    with _get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM expenses WHERE id = ?", (expense_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_summary(month: str | None = None) -> list[dict]:
    """Return per-category totals, optionally restricted to a single month.

    Args:
        month: Optional 'YYYY-MM' string to filter by. When omitted, all
               expenses are included in the totals.

    Returns:
        A list of dicts with keys 'category' and 'total' (as Decimal),
        ordered by total descending.
    """
    with _get_connection() as conn:
        if month:
            rows = conn.execute(
                """
                SELECT category, amount
                FROM expenses
                WHERE strftime('%Y-%m', date) = ?
                ORDER BY category
                """,
                (month,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT category, amount FROM expenses ORDER BY category"
            ).fetchall()

    # Aggregate totals using Decimal arithmetic
    totals: dict[str, Decimal] = {}
    for row in rows:
        cat = row["category"]
        totals[cat] = totals.get(cat, Decimal("0")) + Decimal(row["amount"])

    return sorted(
        [{"category": cat, "total": total} for cat, total in totals.items()],
        key=lambda x: x["total"],
        reverse=True,
    )
