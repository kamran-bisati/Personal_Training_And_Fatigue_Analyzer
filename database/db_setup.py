"""SQLite database setup for the Fitness Analytics & Training Intelligence System.

Phase 3 deliverable:

* ``get_connection()``  - opens a connection with foreign keys enforced
* ``init_db()``         - creates the 8-table schema
* ``seed_exercises()``  - populates the exercise library
* ``reset_db()``        - wipes everything and starts fresh (tests & demos)

Schema tables:

users, exercises, workout_sessions, workout_sets, recovery_logs,
training_programs, program_days, program_exercises

Dates are stored as ISO text (``YYYY-MM-DD``), which is the SQLite convention.
Foreign keys cascade on delete so removing a user cleanly removes their
sessions, sets, recovery logs and programs.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path("database/fitness.db")

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    age           INTEGER,
    height_cm     REAL,
    weight_kg     REAL,
    goal          TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS exercises (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               TEXT NOT NULL,
    primary_muscle_group   TEXT NOT NULL,
    secondary_muscle_group TEXT,
    equipment          TEXT NOT NULL,
    is_custom          INTEGER NOT NULL DEFAULT 0,
    created_by_user_id INTEGER,
    created_at         TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS workout_sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    session_date TEXT NOT NULL,        -- YYYY-MM-DD
    duration_min INTEGER,
    notes        TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, session_date)
);

CREATE TABLE IF NOT EXISTS workout_sets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    INTEGER NOT NULL,
    exercise_id   INTEGER NOT NULL,
    set_number    INTEGER NOT NULL,
    reps          INTEGER NOT NULL CHECK (reps > 0),
    weight_kg     REAL NOT NULL CHECK (weight_kg >= 0),
    rpe           REAL CHECK (rpe >= 1 AND rpe <= 10),
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES workout_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recovery_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    log_date      TEXT NOT NULL,        -- YYYY-MM-DD
    sleep_hours   REAL CHECK (sleep_hours >= 0 AND sleep_hours <= 24),
    body_weight_kg REAL CHECK (body_weight_kg >= 30 AND body_weight_kg <= 300),
    soreness      INTEGER CHECK (soreness >= 1 AND soreness <= 10),
    energy        INTEGER CHECK (energy >= 1 AND energy <= 10),
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, log_date)
);

CREATE TABLE IF NOT EXISTS training_programs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    name       TEXT NOT NULL,
    split_type TEXT NOT NULL,          -- 'PPL', 'Upper/Lower', 'Full Body', 'Custom'
    is_active  INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS program_days (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id  INTEGER NOT NULL,
    day_name    TEXT NOT NULL,
    day_order   INTEGER NOT NULL,
    FOREIGN KEY (program_id) REFERENCES training_programs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS program_exercises (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    program_day_id    INTEGER NOT NULL,
    exercise_id       INTEGER NOT NULL,
    target_sets       INTEGER CHECK (target_sets > 0),
    target_reps       INTEGER CHECK (target_reps > 0),
    target_weight_kg  REAL,
    notes             TEXT,
    FOREIGN KEY (program_day_id) REFERENCES program_days(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
);
"""

EXERCISE_SEED: list[dict] = [
    {
        "name": "Bench Press",
        "primary_muscle_group": "Chest",
        "secondary_muscle_group": "Shoulders",
        "equipment": "Barbell",
    },
    {
        "name": "Overhead Press",
        "primary_muscle_group": "Shoulders",
        "secondary_muscle_group": "Triceps",
        "equipment": "Barbell",
    },
    {
        "name": "Triceps Pushdown",
        "primary_muscle_group": "Arms",
        "secondary_muscle_group": None,
        "equipment": "Cable",
    },
    {
        "name": "Back Squat",
        "primary_muscle_group": "Legs",
        "secondary_muscle_group": "Back",
        "equipment": "Barbell",
    },
    {
        "name": "Romanian Deadlift",
        "primary_muscle_group": "Legs",
        "secondary_muscle_group": "Back",
        "equipment": "Barbell",
    },
    {
        "name": "Leg Press",
        "primary_muscle_group": "Legs",
        "secondary_muscle_group": None,
        "equipment": "Machine",
    },
    {
        "name": "Deadlift",
        "primary_muscle_group": "Back",
        "secondary_muscle_group": "Legs",
        "equipment": "Barbell",
    },
    {
        "name": "Barbell Row",
        "primary_muscle_group": "Back",
        "secondary_muscle_group": "Arms",
        "equipment": "Barbell",
    },
    {
        "name": "Pull-Up",
        "primary_muscle_group": "Back",
        "secondary_muscle_group": "Arms",
        "equipment": "Bodyweight",
    },
    {
        "name": "Biceps Curl",
        "primary_muscle_group": "Arms",
        "secondary_muscle_group": None,
        "equipment": "Dumbbell",
    },
]


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with row_factory and foreign keys enabled."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create all tables if they don't exist yet."""
    conn.executescript(SCHEMA)
    conn.commit()


def seed_exercises(conn: sqlite3.Connection) -> int:
    """Insert the default exercise library. Skips rows that already exist."""
    inserted = 0
    for exercise in EXERCISE_SEED:
        existing = conn.execute(
            "SELECT id FROM exercises WHERE name = ?", (exercise["name"],)
        ).fetchone()
        if existing:
            continue
        conn.execute(
            """
            INSERT INTO exercises
                (name, primary_muscle_group, secondary_muscle_group, equipment, is_custom)
            VALUES (?, ?, ?, ?, 0)
            """,
            (
                exercise["name"],
                exercise["primary_muscle_group"],
                exercise["secondary_muscle_group"],
                exercise["equipment"],
            ),
        )
        inserted += 1
    conn.commit()
    return inserted


def reset_db(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Drop every table, recreate the schema and seed the exercise library."""
    conn = get_connection(db_path)
    conn.executescript(
        """
        DROP TABLE IF EXISTS program_exercises;
        DROP TABLE IF EXISTS program_days;
        DROP TABLE IF EXISTS training_programs;
        DROP TABLE IF EXISTS recovery_logs;
        DROP TABLE IF EXISTS workout_sets;
        DROP TABLE IF EXISTS workout_sessions;
        DROP TABLE IF EXISTS exercises;
        DROP TABLE IF EXISTS users;
        """
    )
    conn.commit()
    init_db(conn)
    seed_exercises(conn)
    return conn
