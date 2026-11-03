"""
Database Seeder for Testing and QA Accounts.
Seeds both root and backend SQLite databases.
"""

import sqlite3
import uuid
from datetime import datetime
from app.core.security import get_password_hash

DB_PATHS = ["rppg_local.db", "backend/rppg_local.db"]

TEST_ACCOUNTS = [
    {
        "email": "demo_researcher@fyp.edu",
        "password": "ResearchPassword123!",
        "full_name": "Dr. Demo Researcher (Lead)",
    },
    {
        "email": "biomedical_tester@fyp.edu",
        "password": "TestPassword123!",
        "full_name": "Biomedical Engineering Tester",
    },
    {
        "email": "test_user@fyp.edu",
        "password": "TestUser2026!",
        "full_name": "Student QA Tester",
    },
]


def seed_database(path: str):
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    for acc in TEST_ACCOUNTS:
        cursor.execute("SELECT id, pseudonym_id FROM users WHERE email = ?", (acc["email"],))
        row = cursor.fetchone()
        user_id = row[0] if row else str(uuid.uuid4())
        pseudonym_id = row[1] if row else f"SUBJ-{uuid.uuid4().hex[:8].upper()}"
        hashed = get_password_hash(acc["password"])
        now = datetime.utcnow().isoformat()

        cursor.execute(
            """
            INSERT OR REPLACE INTO users (
                id, email, hashed_password, full_name, pseudonym_id, consent_accepted, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, 1, 1, ?)
            """,
            (user_id, acc["email"], hashed, acc["full_name"], pseudonym_id, now),
        )

    conn.commit()
    cursor.execute("SELECT email, full_name, is_active FROM users")
    users = cursor.fetchall()
    print(f"[{path}] Active users count: {len(users)}")
    for u in users:
        print(f"  - {u[0]}: {u[1]}")
    conn.close()


def main():
    for p in DB_PATHS:
        try:
            seed_database(p)
        except Exception as e:
            print(f"Skipping {p}: {e}")


if __name__ == "__main__":
    main()
