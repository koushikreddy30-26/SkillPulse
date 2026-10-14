
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "skillpulse.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _add_user_id_column(conn, table_name):
    """Add user_id to an existing table without deleting existing data."""
    columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if "user_id" not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN user_id INTEGER")


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT 'Learner',
                career_goal TEXT NOT NULL,
                current_skills TEXT NOT NULL,
                required_skills TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER,
                career_goal TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER,
                target_skill TEXT NOT NULL,
                recommendations_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER
            )
        """)

        # Safely migrate databases created by the older version.
        _add_user_id_column(conn, "profiles")
        _add_user_id_column(conn, "saved_plans")
        _add_user_id_column(conn, "saved_recommendations")

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles(user_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_saved_plans_user_id ON saved_plans(user_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_saved_recommendations_user_id "
            "ON saved_recommendations(user_id)"
        )


def save_profile(name, career_goal, current_skills, required_skills, user_id):
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO profiles
                (name, career_goal, current_skills, required_skills, user_id)
            VALUES (?, ?, ?, ?, ?)
        """, (name, career_goal, current_skills, required_skills, user_id))
        return cursor.lastrowid


def list_profiles(user_id):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM profiles
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,)).fetchall()
        return [dict(row) for row in rows]


def profile_belongs_to_user(profile_id, user_id):
    if profile_id is None:
        return True

    with get_connection() as conn:
        row = conn.execute("""
            SELECT id FROM profiles
            WHERE id = ? AND user_id = ?
        """, (profile_id, user_id)).fetchone()
        return row is not None


def save_plan(profile_id, career_goal, plan, user_id):
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO saved_plans
                (profile_id, career_goal, plan_json, user_id)
            VALUES (?, ?, ?, ?)
        """, (profile_id, career_goal, json.dumps(plan), user_id))
        return cursor.lastrowid


def list_plans(user_id):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM saved_plans
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,)).fetchall()

        results = []
        for row in rows:
            item = dict(row)
            item["plan"] = json.loads(item.pop("plan_json"))
            results.append(item)
        return results


def save_recommendations(
    profile_id, target_skill, recommendations, user_id
):
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO saved_recommendations
                (profile_id, target_skill, recommendations_json, user_id)
            VALUES (?, ?, ?, ?)
        """, (
            profile_id,
            target_skill,
            json.dumps(recommendations),
            user_id
        ))
        return cursor.lastrowid


def list_saved_recommendations(user_id):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM saved_recommendations
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,)).fetchall()

        results = []
        for row in rows:
            item = dict(row)
            item["recommendations"] = json.loads(
                item.pop("recommendations_json")
            )
            results.append(item)
        return results
