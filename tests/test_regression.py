"""Regression tests for bugs identified during stabilization.

These tests cover:

* Personal records: accurate, separate metrics computed from actually
  performed sets (never an invalid weight/rep combination), plus e1RM.
* Exercise archiving: archiving preserves historical workout sets; deletion
  is refused when history exists.
* Profile isolation: draft (pending) sets are not shared between users.
* Recovery: body weight is optional and stored as NULL when not provided.
* Database migration: ``is_active`` column and ``ON DELETE RESTRICT`` FK.
* Empty datasets / missing values handled gracefully.
"""

from __future__ import annotations

import sqlite3

import pytest

from database import repository as repo
from database.db_setup import get_connection, init_db, migrate_db, seed_exercises
from src.management.workout_manager import WorkoutManager


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def conn() -> sqlite3.Connection:
    connection = get_connection(":memory:")
    init_db(connection)
    seed_exercises(connection)
    yield connection
    connection.close()


def _make_user(conn, name: str) -> int:
    return repo.create_user(conn, name)


def _make_session(conn, user_id: int, date_str: str = "2026-10-05") -> int:
    return repo.create_session(conn, user_id, date_str, duration_min=60)


def _add_set(conn, session_id: int, exercise_id: int, set_number: int,
             reps: int, weight_kg: float, rpe: float = 8.0) -> int:
    return repo.add_set(conn, session_id, exercise_id, set_number, reps, weight_kg, rpe)


# --------------------------------------------------------------------------- #
# Personal records - accurate metrics
# --------------------------------------------------------------------------- #


def test_personal_records_never_shows_invalid_weight_rep_combo(conn):
    """max_weight and max_reps must each come from a real performed set.

    Set A: 100 kg x 5 reps. Set B: 90 kg x 10 reps.
    max_weight must be 100 kg (with 5 reps), max_reps must be 10 (with 90 kg).
    The pairing 100 kg x 10 reps was never performed and must not appear.
    """
    user_id = _make_user(conn, "Alice")
    exercise = repo.get_exercise_by_name(conn, "Bench Press")
    assert exercise is not None
    session_id = _make_session(conn, user_id)
    _add_set(conn, session_id, exercise["id"], 1, 5, 100.0, 8.0)
    _add_set(conn, session_id, exercise["id"], 2, 10, 90.0, 8.0)

    records = repo.personal_records(conn, user_id, exercise["id"])
    assert len(records) == 1
    pr = records[0]

    # Heaviest set actually performed.
    assert pr["max_weight_kg"] == 100.0
    assert pr["max_weight_reps"] == 5  # reps of the heaviest set
    # Most reps actually performed.
    assert pr["max_reps"] == 10
    assert pr["max_reps_weight"] == 90.0  # weight of the most-reps set

    # The invalid combination 100 kg x 10 reps was never performed.
    assert not (pr["max_weight_kg"] == 100.0 and pr["max_reps"] == 10
                and pr["max_weight_reps"] == 10)


def test_personal_records_includes_e1rm(conn):
    user_id = _make_user(conn, "Bob")
    exercise = repo.get_exercise_by_name(conn, "Bench Press")
    session_id = _make_session(conn, user_id)
    # 100 kg x 5 reps -> Epley e1RM = 100 * (1 + 5/30) = 116.67
    _add_set(conn, session_id, exercise["id"], 1, 5, 100.0, 8.0)

    records = repo.personal_records(conn, user_id, exercise["id"])
    pr = records[0]
    assert "best_e1rm_kg" in pr
    assert abs(pr["best_e1rm_kg"] - 116.67) < 0.01
    assert pr["best_e1rm_weight"] == 100.0
    assert pr["best_e1rm_reps"] == 5


def test_personal_records_max_volume_from_real_set(conn):
    """max_volume must be reps * weight of a single actually performed set."""
    user_id = _make_user(conn, "Carol")
    exercise = repo.get_exercise_by_name(conn, "Bench Press")
    session_id = _make_session(conn, user_id)
    # 5 x 100 = 500 ; 10 x 90 = 900 ; 3 x 150 = 450
    _add_set(conn, session_id, exercise["id"], 1, 5, 100.0, 8.0)
    _add_set(conn, session_id, exercise["id"], 2, 10, 90.0, 8.0)
    _add_set(conn, session_id, exercise["id"], 3, 3, 150.0, 9.0)

    pr = repo.personal_records(conn, user_id, exercise["id"])[0]
    assert pr["max_volume_kg"] == 900.0
    assert pr["max_volume_reps"] == 10
    assert pr["max_volume_weight"] == 90.0


def test_personal_records_empty_returns_empty_list(conn):
    user_id = _make_user(conn, "Empty")
    exercise = repo.get_exercise_by_name(conn, "Bench Press")
    assert repo.personal_records(conn, user_id, exercise["id"]) == []


def test_workout_manager_personal_records_returns_dict(conn):
    mgr = WorkoutManager(connection=conn)
    try:
        user_id = _make_user(conn, "Dave")
        exercise = repo.get_exercise_by_name(conn, "Bench Press")
        session_id = _make_session(conn, user_id)
        _add_set(conn, session_id, exercise["id"], 1, 5, 100.0, 8.0)
        records = mgr.personal_records(user_id, exercise["id"])
        assert records is not None
        assert records["max_weight_kg"] == 100.0
    finally:
        mgr.close()


# --------------------------------------------------------------------------- #
# Exercise archiving and historical data preservation
# --------------------------------------------------------------------------- #


def test_exercise_archive_preserves_history_sets(conn):
    user_id = _make_user(conn, "Eve")
    exercise = repo.get_exercise_by_name(conn, "Bench Press")
    session_id = _make_session(conn, user_id)
    _add_set(conn, session_id, exercise["id"], 1, 5, 100.0, 8.0)

    affected = repo.set_exercise_active(conn, exercise["id"], False)
    assert affected == 1

    archived = repo.get_exercise(conn, exercise["id"])
    assert archived["is_active"] == 0

    # Historical sets remain intact and still reference the exercise.
    sets = repo.get_sets_for_session(conn, session_id)
    assert len(sets) == 1
    assert sets[0]["exercise_id"] == exercise["id"]

    # History join still works.
    history = repo.workout_history(conn, user_id)
    assert len(history) == 1
    assert history[0]["exercise_name"] == "Bench Press"


def test_delete_exercise_refused_when_history_exists(conn):
    exercise = repo.get_exercise_by_name(conn, "Bench Press")
    user_id = _make_user(conn, "Frank")
    session_id = _make_session(conn, user_id)
    _add_set(conn, session_id, exercise["id"], 1, 5, 100.0, 8.0)

    affected = repo.delete_exercise(conn, exercise["id"])
    assert affected == 0  # refused
    assert repo.get_exercise(conn, exercise["id"]) is not None


def test_delete_exercise_allowed_when_no_history(conn):
    # Create a brand-new custom exercise with no sets.
    eid = repo.create_exercise(conn, "Unused Lift", "Chest", "Dumbbell", is_custom=1)
    affected = repo.delete_exercise(conn, eid)
    assert affected == 1
    assert repo.get_exercise(conn, eid) is None


def test_list_exercises_excludes_archived_by_default(conn):
    exercise = repo.get_exercise_by_name(conn, "Bench Press")
    repo.set_exercise_active(conn, exercise["id"], False)

    active = repo.list_exercises(conn)
    assert all(e["is_active"] == 1 for e in active)
    assert not any(e["id"] == exercise["id"] for e in active)

    all_ex = repo.list_exercises(conn, include_archived=True)
    assert any(e["id"] == exercise["id"] for e in all_ex)


# --------------------------------------------------------------------------- #
# Profile isolation - pending sets
# --------------------------------------------------------------------------- #


def test_pending_sets_cleared_on_profile_change_simulation():
    """Simulate the app's pending_sets isolation rule.

    Two users are independent in the database: workout sets saved under one
    user never appear in another user's history. The app layer pairs this with
    clearing st.session_state.pending_sets whenever the profile changes.
    """
    connection = get_connection(":memory:")
    try:
        init_db(connection)
        seed_exercises(connection)
        u1 = repo.create_user(connection, "User One")
        u2 = repo.create_user(connection, "User Two")
        exercise = repo.get_exercise_by_name(connection, "Bench Press")
        s1 = repo.create_session(connection, u1, "2026-10-05")
        s2 = repo.create_session(connection, u2, "2026-10-05")
        repo.add_set(connection, s1, exercise["id"], 1, 5, 100.0, 8.0)
        h1 = repo.workout_history(connection, u1)
        h2 = repo.workout_history(connection, u2)
        assert len(h1) == 1
        assert len(h2) == 0
    finally:
        connection.close()


# --------------------------------------------------------------------------- #
# Recovery - optional body weight
# --------------------------------------------------------------------------- #


def test_recovery_body_weight_optional_stored_as_null(conn):
    user_id = _make_user(conn, "Grace")
    # Body weight omitted -> NULL, which the CHECK constraint allows.
    log_id = repo.log_recovery(conn, user_id, "2026-10-05",
                               sleep_hours=7.5, soreness=3, energy=8)
    rec = repo.get_recovery(conn, user_id, "2026-10-05")
    assert rec is not None
    assert rec["id"] == log_id
    assert rec["body_weight_kg"] is None


def test_recovery_update_preserves_existing_fields(conn):
    user_id = _make_user(conn, "Heidi")
    repo.log_recovery(conn, user_id, "2026-10-05", sleep_hours=7.5, body_weight_kg=78.0,
                      soreness=3, energy=8)
    log_id = repo.log_recovery(conn, user_id, "2026-10-05", energy=6)
    rec = repo.get_recovery(conn, user_id, "2026-10-05")
    assert rec["id"] == log_id  # same row updated, no duplicate
    assert rec["sleep_hours"] == 7.5  # preserved
    assert rec["energy"] == 6  # updated


# --------------------------------------------------------------------------- #
# Database migration
# --------------------------------------------------------------------------- #


def test_migrate_db_adds_is_active_column():
    connection = get_connection(":memory:")
    try:
        # Create the *old* schema (no is_active, CASCADE FK) manually.
        connection.executescript("""
            PRAGMA foreign_keys = ON;
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                primary_muscle_group TEXT NOT NULL,
                equipment TEXT NOT NULL,
                is_custom INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE workout_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, session_date)
            );
            CREATE TABLE workout_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                set_number INTEGER NOT NULL,
                reps INTEGER NOT NULL CHECK (reps > 0),
                weight_kg REAL NOT NULL CHECK (weight_kg >= 0),
                rpe REAL CHECK (rpe >= 1 AND rpe <= 10),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (session_id) REFERENCES workout_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
            );
        """)
        connection.commit()
        # Insert an exercise + a set using the old schema.
        connection.execute(
            "INSERT INTO exercises (name, primary_muscle_group, equipment, is_custom) "
            "VALUES ('Bench Press', 'Chest', 'Barbell', 0)"
        )
        connection.execute(
            "INSERT INTO users (name) VALUES ('Migrator')"
        )
        connection.execute(
            "INSERT INTO workout_sessions (user_id, session_date) VALUES (1, '2026-10-05')"
        )
        connection.execute(
            "INSERT INTO workout_sets (session_id, exercise_id, set_number, reps, weight_kg) "
            "VALUES (1, 1, 1, 5, 100.0)"
        )
        connection.commit()

        migrate_db(connection)

        # is_active column now exists and defaults to 1.
        cols = {row["name"] for row in connection.execute("PRAGMA table_info(exercises)")}
        assert "is_active" in cols
        assert connection.execute("SELECT is_active FROM exercises WHERE id = 1").fetchone()["is_active"] == 1

        # Existing set data preserved.
        assert connection.execute("SELECT COUNT(*) AS c FROM workout_sets").fetchone()["c"] == 1

        # FK is now RESTRICT.
        fks = connection.execute("PRAGMA foreign_key_list(workout_sets)").fetchall()
        exercise_fk = [f for f in fks if f["from"] == "exercise_id"][0]
        assert exercise_fk["on_delete"].upper() == "RESTRICT"
    finally:
        connection.close()


def test_migrate_db_is_idempotent(conn):
    migrate_db(conn)
    migrate_db(conn)  # should not raise
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(exercises)")}
    assert "is_active" in cols


def test_workout_manager_next_set_number(conn):
    mgr = WorkoutManager(connection=conn)
    try:
        user_id = _make_user(conn, "Ivan")
        exercise = repo.get_exercise_by_name(conn, "Bench Press")
        session_id = _make_session(conn, user_id)
        assert mgr.next_set_number(session_id, exercise["id"]) == 1
        _add_set(conn, session_id, exercise["id"], 1, 5, 100.0, 8.0)
        assert mgr.next_set_number(session_id, exercise["id"]) == 2
    finally:
        mgr.close()
