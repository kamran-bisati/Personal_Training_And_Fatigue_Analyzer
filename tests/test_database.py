"""Tests for the Phase 3 database schema and CRUD layer.

Uses an in-memory SQLite database so no files are written to disk.
"""

from __future__ import annotations

import sqlite3

import pytest

from database.db_setup import get_connection, init_db, reset_db, seed_exercises
import database.repository as repo


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn() -> sqlite3.Connection:
    connection = get_connection(":memory:")
    init_db(connection)
    seed_exercises(connection)
    yield connection
    connection.close()


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


def test_get_connection_enforces_foreign_keys(conn: sqlite3.Connection) -> None:
    result = conn.execute("PRAGMA foreign_keys").fetchone()
    assert result["foreign_keys"] == 1


def test_schema_has_expected_tables(conn: sqlite3.Connection) -> None:
    tables = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    }
    expected = {
        "users",
        "exercises",
        "workout_sessions",
        "workout_sets",
        "recovery_logs",
        "training_programs",
        "program_days",
        "program_exercises",
    }
    assert expected.issubset(tables)


def test_seed_exercises_inserts_default_library(conn: sqlite3.Connection) -> None:
    exercises = repo.list_exercises(conn)
    assert len(exercises) == 10
    names = {row["name"] for row in exercises}
    assert names == {
        "Bench Press",
        "Overhead Press",
        "Triceps Pushdown",
        "Back Squat",
        "Romanian Deadlift",
        "Leg Press",
        "Deadlift",
        "Barbell Row",
        "Pull-Up",
        "Biceps Curl",
    }


def test_seed_exercises_is_idempotent() -> None:
    connection = get_connection(":memory:")
    try:
        init_db(connection)
        first = seed_exercises(connection)
        second = seed_exercises(connection)
        assert first == 10
        assert second == 0
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


def test_create_and_get_user(conn: sqlite3.Connection) -> None:
    user_id = repo.create_user(conn, "Mir", age=30, height_cm=180.0, weight_kg=78.0, goal="strength")
    user = repo.get_user(conn, user_id)
    assert user is not None
    assert user["name"] == "Mir"
    assert user["age"] == 30
    assert user["height_cm"] == 180.0
    assert user["weight_kg"] == 78.0
    assert user["created_at"] is not None


def test_get_user_missing_returns_none(conn: sqlite3.Connection) -> None:
    assert repo.get_user(conn, 99999) is None


def test_get_user_by_name(conn: sqlite3.Connection) -> None:
    repo.create_user(conn, "Mir")
    assert repo.get_user_by_name(conn, "Mir") is not None
    assert repo.get_user_by_name(conn, "Nobody") is None


def test_update_user(conn: sqlite3.Connection) -> None:
    user_id = repo.create_user(conn, "Mir", weight_kg=78.0)
    affected = repo.update_user(conn, user_id, weight_kg=80.0, goal="hypertrophy")
    assert affected == 1
    user = repo.get_user(conn, user_id)
    assert user["weight_kg"] == 80.0
    assert user["goal"] == "hypertrophy"


def test_delete_user_cascades(conn: sqlite3.Connection) -> None:
    user_id = repo.create_user(conn, "Mir")
    exercise = repo.get_exercise_by_name(conn, "Bench Press")
    session_id = repo.create_session(conn, user_id, "2026-10-05", duration_min=60)
    repo.add_set(conn, session_id, exercise["id"], 1, 5, 80.0, 8.0)
    repo.log_recovery(conn, user_id, "2026-10-05", sleep_hours=7.5, soreness=3, energy=8)

    repo.delete_user(conn, user_id)

    assert repo.get_user(conn, user_id) is None
    assert repo.list_sessions_by_user(conn, user_id) == []
    assert repo.list_recovery_by_user(conn, user_id) == []


# ---------------------------------------------------------------------------
# Exercises
# ---------------------------------------------------------------------------


def test_create_and_get_exercise(conn: sqlite3.Connection) -> None:
    exercise_id = repo.create_exercise(
        conn, "Custom Lift", "Chest", "Dumbbell", secondary_muscle_group="Triceps", is_custom=1
    )
    exercise = repo.get_exercise(conn, exercise_id)
    assert exercise is not None
    assert exercise["name"] == "Custom Lift"
    assert exercise["primary_muscle_group"] == "Chest"
    assert exercise["is_custom"] == 1


def test_list_exercises_filtered(conn: sqlite3.Connection) -> None:
    chest = repo.list_exercises(conn, primary_muscle_group="Chest")
    assert all(row["primary_muscle_group"] == "Chest" for row in chest)
    barbells = repo.list_exercises(conn, equipment="Barbell")
    assert all(row["equipment"] == "Barbell" for row in barbells)


# ---------------------------------------------------------------------------
# Sessions and sets
# ---------------------------------------------------------------------------


def test_create_session_and_add_set(conn: sqlite3.Connection) -> None:
    user_id = repo.create_user(conn, "Mir")
    exercise = repo.get_exercise_by_name(conn, "Bench Press")
    assert exercise is not None

    session_id = repo.create_session(conn, user_id, "2026-10-05", duration_min=60)
    session = repo.get_session(conn, session_id)
    assert session is not None
    assert session["user_id"] == user_id
    assert session["session_date"] == "2026-10-05"

    set_id = repo.add_set(conn, session_id, exercise["id"], 1, 5, 80.0, 8.0)
    sets = repo.get_sets_for_session(conn, session_id)
    assert len(sets) == 1
    assert sets[0]["reps"] == 5
    assert sets[0]["weight_kg"] == 80.0
    assert sets[0]["rpe"] == 8.0
    assert sets[0]["exercise_name"] == "Bench Press"


def test_duplicate_session_date_rejected(conn: sqlite3.Connection) -> None:
    user_id = repo.create_user(conn, "Mir")
    repo.create_session(conn, user_id, "2026-10-05")
    with pytest.raises(sqlite3.IntegrityError):
        repo.create_session(conn, user_id, "2026-10-05")


def test_invalid_reps_rejected_by_check_constraint(conn: sqlite3.Connection) -> None:
    user_id = repo.create_user(conn, "Mir")
    exercise = repo.get_exercise_by_name(conn, "Bench Press")
    session_id = repo.create_session(conn, user_id, "2026-10-05")
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_set(conn, session_id, exercise["id"], 1, -8, 80.0, 8.0)


def test_invalid_rpe_rejected_by_check_constraint(conn: sqlite3.Connection) -> None:
    user_id = repo.create_user(conn, "Mir")
    exercise = repo.get_exercise_by_name(conn, "Bench Press")
    session_id = repo.create_session(conn, user_id, "2026-10-05")
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_set(conn, session_id, exercise["id"], 1, 5, 80.0, 15.0)


def test_set_cascades_on_session_delete(conn: sqlite3.Connection) -> None:
    user_id = repo.create_user(conn, "Mir")
    exercise = repo.get_exercise_by_name(conn, "Bench Press")
    session_id = repo.create_session(conn, user_id, "2026-10-05")
    repo.add_set(conn, session_id, exercise["id"], 1, 5, 80.0, 8.0)

    repo.delete_session(conn, session_id)
    assert repo.get_sets_for_session(conn, session_id) == []


# ---------------------------------------------------------------------------
# Recovery logs
# ---------------------------------------------------------------------------


def test_log_and_get_recovery(conn: sqlite3.Connection) -> None:
    user_id = repo.create_user(conn, "Mir")
    log_id = repo.log_recovery(
        conn, user_id, "2026-10-05", sleep_hours=7.5, body_weight_kg=78.0, soreness=3, energy=8
    )
    recovery = repo.get_recovery(conn, user_id, "2026-10-05")
    assert recovery is not None
    assert recovery["id"] == log_id
    assert recovery["sleep_hours"] == 7.5
    assert recovery["energy"] == 8


def test_log_recovery_updates_existing_date(conn: sqlite3.Connection) -> None:
    user_id = repo.create_user(conn, "Mir")
    repo.log_recovery(conn, user_id, "2026-10-05", sleep_hours=7.5)
    log_id = repo.log_recovery(conn, user_id, "2026-10-05", energy=6)
    recovery = repo.get_recovery(conn, user_id, "2026-10-05")
    assert recovery["id"] == log_id  # same row updated
    assert recovery["sleep_hours"] == 7.5  # preserved
    assert recovery["energy"] == 6  # updated


def test_duplicate_recovery_date_is_one_row(conn: sqlite3.Connection) -> None:
    user_id = repo.create_user(conn, "Mir")
    repo.log_recovery(conn, user_id, "2026-10-05", sleep_hours=7.5)
    repo.log_recovery(conn, user_id, "2026-10-05", sleep_hours=6.0)
    rows = repo.list_recovery_by_user(conn, user_id)
    assert len(rows) == 1


def test_invalid_energy_rejected(conn: sqlite3.Connection) -> None:
    user_id = repo.create_user(conn, "Mir")
    with pytest.raises(sqlite3.IntegrityError):
        repo.log_recovery(conn, user_id, "2026-10-05", energy=11)


# ---------------------------------------------------------------------------
# Programs
# ---------------------------------------------------------------------------


def test_create_program_with_days_and_exercises(conn: sqlite3.Connection) -> None:
    user_id = repo.create_user(conn, "Mir")
    program_id = repo.create_program(conn, user_id, "Push Pull Legs", "PPL")

    day_id = repo.create_program_day(conn, program_id, "Push", 1)
    exercise = repo.get_exercise_by_name(conn, "Bench Press")
    assert exercise is not None
    repo.add_program_exercise(conn, day_id, exercise["id"], target_sets=4, target_reps=5)

    days = repo.list_program_days_with_exercises(conn, program_id)
    assert len(days) == 1
    assert days[0]["day_name"] == "Push"
    assert days[0]["exercise_name"] == "Bench Press"
    assert days[0]["target_sets"] == 4


# ---------------------------------------------------------------------------
# Joined views
# ---------------------------------------------------------------------------


def test_workout_history_joins_session_and_exercise(conn: sqlite3.Connection) -> None:
    user_id = repo.create_user(conn, "Mir")
    exercise = repo.get_exercise_by_name(conn, "Bench Press")
    session_id = repo.create_session(conn, user_id, "2026-10-05", duration_min=60)
    repo.add_set(conn, session_id, exercise["id"], 1, 5, 80.0, 8.0)

    history = repo.workout_history(conn, user_id)
    assert len(history) == 1
    row = history[0]
    assert row["session_date"] == "2026-10-05"
    assert row["duration_min"] == 60
    assert row["exercise_name"] == "Bench Press"


def test_personal_records(conn: sqlite3.Connection) -> None:
    user_id = repo.create_user(conn, "Mir")
    exercise = repo.get_exercise_by_name(conn, "Bench Press")
    session_id = repo.create_session(conn, user_id, "2026-10-05")
    repo.add_set(conn, session_id, exercise["id"], 1, 5, 80.0, 8.0)
    repo.add_set(conn, session_id, exercise["id"], 2, 5, 85.0, 8.5)

    records = repo.personal_records(conn, user_id, exercise["id"])
    assert len(records) == 1
    assert records[0]["max_weight_kg"] == 85.0
    assert records[0]["max_reps"] == 5


# ---------------------------------------------------------------------------
# reset_db
# ---------------------------------------------------------------------------


def test_reset_db_recreates_schema() -> None:
    connection = reset_db(":memory:")
    try:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "users" in tables
        assert "exercises" in tables
        exercises = repo.list_exercises(connection)
        assert len(exercises) == 10
    finally:
        connection.close()
