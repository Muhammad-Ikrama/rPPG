"""
Database Seeder for Development / QA Researcher Accounts.
Seeds the canonical SQLite database anchored at PROJECT_ROOT.
Note: Credentials seeded here are for local dev/evaluator testing only and are never bundled into the APK.
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from app.core.config import PROJECT_ROOT
from app.core.security import get_password_hash
from app.db.session import init_db
import asyncio

DB_PATH = str(PROJECT_ROOT / "rppg_local.db")

TEST_ACCOUNTS = [
    {
        "email": "demo_researcher@fyp.edu",
        "password": "ResearchPassword123!",
        "full_name": "Dr. Demo Researcher (Lead)",
        "role": "researcher",
    },
    {
        "email": "biomedical_tester@fyp.edu",
        "password": "TestPassword123!",
        "full_name": "Biomedical Engineering Tester",
        "role": "researcher",
    },
    {
        "email": "member1@fyp.edu",
        "password": "Member1Pass2026!",
        "full_name": "FYP Group Member 1",
        "role": "researcher",
    },
    {
        "email": "member2@fyp.edu",
        "password": "Member2Pass2026!",
        "full_name": "FYP Group Member 2",
        "role": "researcher",
    },
    {
        "email": "member3@fyp.edu",
        "password": "Member3Pass2026!",
        "full_name": "FYP Group Member 3",
        "role": "researcher",
    },
    {
        "email": "member4@fyp.edu",
        "password": "Member4Pass2026!",
        "full_name": "FYP Group Member 4",
        "role": "researcher",
    },
    {
        "email": "fyp_evaluator@fyp.edu",
        "password": "EvaluatorPass2026!",
        "full_name": "FYP Project Evaluator / Supervisor",
        "role": "evaluator",
    },
]


def seed_database(path: str = DB_PATH):
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    for acc in TEST_ACCOUNTS:
        email = acc["email"].strip().lower()
        cursor.execute("SELECT id, pseudonym_id FROM users WHERE LOWER(email) = ?", (email,))
        row = cursor.fetchone()
        user_id = row[0] if row else str(uuid.uuid4())
        pseudonym_id = row[1] if row else f"SUBJ-{uuid.uuid4().hex[:8].upper()}"
        hashed = get_password_hash(acc["password"])
        now = datetime.now(timezone.utc).isoformat()

        cursor.execute(
            """
            INSERT OR REPLACE INTO users (
                id, email, hashed_password, full_name, pseudonym_id, role, consent_accepted, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?)
            """,
            (user_id, email, hashed, acc["full_name"], pseudonym_id, acc["role"], now),
        )

    conn.commit()
    cursor.execute("SELECT email, full_name, role, is_active FROM users")
    users = cursor.fetchall()
    print(f"[{path}] Active users count: {len(users)}")
    for u in users:
        print(f"  - {u[0]} ({u[2]}): {u[1]}")
    conn.close()


def main():
    asyncio.run(init_db())
    seed_database(DB_PATH)


if __name__ == "__main__":
    main()
