"""Seed a single random Indian user into the spendly.db database."""

import random
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from werkzeug.security import generate_password_hash

# Common Indian first names spanning regions (North, South, East, West)
FIRST_NAMES = [
    "Rahul", "Priya", "Amit", "Sneha", "Vikram", "Anjali",
    "Arjun", "Pooja", "Rohan", "Kavya", "Aditya", "Meera",
    "Karthik", "Divya", "Rohit", "Ananya", "Suresh", "Lakshmi",
    "Pradeep", "Neha", "Sanjay", "Ritu", "Manoj", "Swati",
    "Naveen", "Deepa", "Sandeep", "Pallavi", "Ganesh", "Nithya",
    "Abhishek", "Shalini", "Rajesh", "Geeta", "Aravind", "Rekha",
    "Vivek", "Asha", "Mukesh", "Sushma",
]

# Common Indian last names spanning regions and communities
LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Gupta", "Iyer", "Reddy",
    "Nair", "Menon", "Pillai", "Banerjee", "Mukherjee", "Chatterjee",
    "Das", "Bose", "Khan", "Ahmed", "Siddiqui", "Kapoor",
    "Singh", "Kaur", "Joshi", "Mehta", "Shah", "Desai",
    "Kulkarni", "Joshi", "Rao", "Naidu", "Subramanian", "Krishnan",
    "Bhat", "Shetty", "Tiwari", "Mishra", "Pandey", "Saxena",
    "Chauhan", "Rathore", "Srinivasan", "Anand",
]


def generate_name():
    """Return a random (first, last) Indian name."""
    return random.choice(FIRST_NAMES), random.choice(LAST_NAMES)


def generate_email(first: str, last: str) -> str:
    """Build an email like rahul.sharma91@gmail.com with a 2-3 digit suffix."""
    suffix_len = random.choice([2, 3])
    suffix = "".join(random.choices("0123456789", k=suffix_len))
    return f"{first.lower()}.{last.lower()}{suffix}@gmail.com"


def email_exists(conn: sqlite3.Connection, email: str) -> bool:
    cursor = conn.execute("SELECT 1 FROM users WHERE email = ?", (email,))
    return cursor.fetchone() is not None


def main():
    db_path = Path(__file__).resolve().parent / "spendly.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        # Ensure schema exists (idempotent).
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        conn.commit()

        # Generate a unique name + email.
        for _ in range(50):
            first, last = generate_name()
            name = f"{first} {last}"
            email = generate_email(first, last)
            if not email_exists(conn, email):
                break
        else:
            raise RuntimeError("Could not generate a unique email after 50 attempts.")

        password_hash = generate_password_hash("password123")
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor = conn.execute(
            """
            INSERT INTO users (name, email, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, email, password_hash, created_at),
        )
        conn.commit()
        user_id = cursor.lastrowid

        # Re-read to confirm persisted state (mirrors get_db() pattern).
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        print(f"User created successfully:")
        print(f"  id    : {row['id']}")
        print(f"  name  : {row['name']}")
        print(f"  email : {row['email']}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()