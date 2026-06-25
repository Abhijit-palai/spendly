import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash


def get_db():
    """Open a SQLite connection with row factory and foreign keys enabled."""
    db_path = Path(__file__).resolve().parent.parent / "spendly.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create users and expenses tables if they don't exist."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        conn.commit()


def seed_db():
    """Insert demo user and sample expenses if no users exist."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] > 0:
            return

        password_hash = generate_password_hash("demo123")
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", password_hash),
        )
        user_id = cursor.lastrowid

        expenses_data = [
            (user_id, 12.50, "Food", "2026-06-01", "Groceries at supermarket"),
            (user_id, 25.00, "Food", "2026-06-05", "Restaurant dinner"),
            (user_id, 45.00, "Transport", "2026-06-03", "Gas refill"),
            (user_id, 15.00, "Transport", "2026-06-10", "Bus pass"),
            (user_id, 80.00, "Bills", "2026-06-02", "Electricity bill"),
            (user_id, 30.00, "Health", "2026-06-07", "Pharmacy purchase"),
            (user_id, 20.00, "Entertainment", "2026-06-04", "Movie tickets"),
            (user_id, 60.00, "Shopping", "2026-06-09", "Clothing purchase"),
            (user_id, 10.00, "Other", "2026-06-06", "Miscellaneous supplies"),
        ]

        cursor.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            expenses_data,
        )

        conn.commit()