"""Tests for the Phase 4 management module."""

from __future__ import annotations

import sqlite3

import pytest

from database import repository as repo
from database.db_setup import get_connection, init_db, reset_db, seed_exercises
from src.management.exercise_manager import ExerciseManager
from src.management.program_manager import ProgramManager
from src.management.workout_manager import WorkoutManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn():
    connection = get_connection(":memory:")
    init_db(connection)
    seed_exercises(connection)
    yield connection
    connection.close()


# ---------------------------------------------------------------------------
# ExerciseManager
# ---------------------------------------------------------------------------


def test_exercise_manager_add_and_get(conn):
    mgr = ExerciseManager(connection=conn)
    try:
        eid = mgr.add_exercise("Test Curl", "Arms", "Dumbbell")
        exercise = mgr.get_exercise(eid)
        assert exercise is not None
        assert exercise["name"] == "Test Curl"
        assert exercise["primary_muscle_group"] == "Arms"
        assert exercise["equipment"] == "Dumbbell"

        by_name = mgr.get_exercise_by_name("Test Curl")
        assert by_name["id"] == eid
    finally:
        mgr.close()


def test_exercise_manager_list_filtered(conn):
    mgr = ExerciseManager(connection=conn)
    try:
        chest = mgr.list_exercises(primary_muscle_group="Chest")
        assert len(chest) >= 1
        assert all(r["primary_muscle_group"] == "Chest" for r in chest)

        barbells = mgr.list_exercises(equipment="Barbell")
        assert all(r["equipment"] == "Barbell" for r in barbells)

        groups = mgr.list_muscle_groups()
        assert "Chest" in groups
        assert "Legs" in groups

        equipment_list = mgr.list_equipment()
        assert "Barbell" in equipment_list

        results = mgr.search("Press")
        assert len(results) >= 1
        assert all("Press" in r["name"] for r in results)
    finally:
        mgr.close()


def test_exercise_manager_update_delete(conn):
    mgr = ExerciseManager(connection=conn)
    try:
        eid = mgr.add_exercise("Temp", "Chest", "Machine")
        assert mgr.update_exercise(eid, name="Temp Updated") == 1
        assert mgr.get_exercise(eid)["name"] == "Temp Updated"
        assert mgr.delete_exercise(eid) == 1
        assert mgr.get_exercise(eid) is None
    finally:
        mgr.close()


# ---------------------------------------------------------------------------
# WorkoutManager
# ---------------------------------------------------------------------------


def test_workout_manager_create_session_and_add_set(conn):
    mgr = WorkoutManager(connection=conn)
    try:
        uid = repo.create_user(conn, "Mir", age=30)
        exercise = repo.get_exercise_by_name(conn, "Bench Press")
        assert exercise is not None

        session_id = mgr.create_session(uid, "2026-10-05", duration_min=60)
        assert mgr.session_exists_on_date(uid, "2026-10-05")

        set_id = mgr.add_set(session_id, exercise["id"], 1, 5, 80.0, 8.0)
        assert set_id is not None

        sets = mgr.get_sets_for_session(session_id)
        assert len(sets) == 1
        assert sets[0]["exercise_name"] == "Bench Press"
        assert sets[0]["weight_kg"] == 80.0
    finally:
        mgr.close()


def test_workout_manager_history_and_records(conn):
    mgr = WorkoutManager(connection=conn)
    try:
        uid = repo.create_user(conn, "Mir")
        exercise = repo.get_exercise_by_name(conn, "Bench Press")
        session_id = mgr.create_session(uid, "2026-10-05")
        mgr.add_set(session_id, exercise["id"], 1, 5, 80.0, 8.0)
        mgr.add_set(session_id, exercise["id"], 2, 5, 85.0, 8.5)

        history = mgr.workout_history(uid)
        assert len(history) == 2
        assert history[0]["exercise_name"] == "Bench Press"

        records = mgr.personal_records(uid, exercise["id"])
        assert records is not None
        assert records["max_weight_kg"] == 85.0
    finally:
        mgr.close()


def test_workout_manager_duplicate_session_rejected(conn):
    mgr = WorkoutManager(connection=conn)
    try:
        uid = repo.create_user(conn, "Mir")
        mgr.create_session(uid, "2026-10-05")
        with pytest.raises(sqlite3.IntegrityError):
            mgr.create_session(uid, "2026-10-05")
    finally:
        mgr.close()


# ---------------------------------------------------------------------------
# ProgramManager
# ---------------------------------------------------------------------------


def test_program_manager_create_program_and_days(conn):
    mgr = ProgramManager(connection=conn)
    try:
        uid = repo.create_user(conn, "Mir")
        pid = mgr.create_program(uid, "My PPL", "PPL")
        day_id = mgr.add_day(pid, "Push", 1)
        exercise = repo.get_exercise_by_name(conn, "Bench Press")
        assert exercise is not None
        mgr.assign_exercise(day_id, exercise["id"], target_sets=4, target_reps=5)

        structure = mgr.get_program_structure(pid)
        assert len(structure) == 1
        assert structure[0]["day_name"] == "Push"
        assert structure[0]["exercise_name"] == "Bench Press"
        assert structure[0]["target_sets"] == 4
    finally:
        mgr.close()


def test_program_manager_create_from_template_ppl(conn):
    mgr = ProgramManager(connection=conn)
    try:
        uid = repo.create_user(conn, "Mir")
        pid = mgr.create_from_template(uid, "PPL Program", "PPL", template="PPL")

        structure = mgr.get_program_structure(pid)
        day_names = {row["day_name"] for row in structure}
        assert day_names == {"Push", "Pull", "Legs"}
        assert len(structure) == 9  # 3 exercises per day x 3 days

        program = mgr.get_program(pid)
        assert program["split_type"] == "PPL"
        assert program["is_active"] == 1
    finally:
        mgr.close()


def test_program_manager_create_from_template_upper_lower(conn):
    mgr = ProgramManager(connection=conn)
    try:
        uid = repo.create_user(conn, "Mir")
        pid = mgr.create_from_template(uid, "UL Program", "Upper/Lower", template="Upper/Lower")

        structure = mgr.get_program_structure(pid)
        day_names = {row["day_name"] for row in structure}
        assert day_names == {"Upper A", "Lower A", "Upper B", "Lower B"}
        assert len(structure) == 20  # 5 exercises per day x 4 days
    finally:
        mgr.close()


def test_program_manager_unknown_template_raises(conn):
    mgr = ProgramManager(connection=conn)
    try:
        uid = repo.create_user(conn, "Mir")
        with pytest.raises(ValueError):
            mgr.create_from_template(uid, "Bad", "Custom", template="Invalid")
    finally:
        mgr.close()


def test_program_manager_list_and_delete(conn):
    mgr = ProgramManager(connection=conn)
    try:
        uid = repo.create_user(conn, "Mir")
        pid = mgr.create_program(uid, "Temp", "Custom")
        programs = mgr.list_programs(uid)
        assert len(programs) == 1
        assert mgr.delete_program(pid) == 1
        assert mgr.list_programs(uid) == []
    finally:
        mgr.close()


def test_program_manager_set_active(conn):
    mgr = ProgramManager(connection=conn)
    try:
        uid = repo.create_user(conn, "Mir")
        pid1 = mgr.create_program(uid, "Prog 1", "PPL")
        pid2 = mgr.create_program(uid, "Prog 2", "Upper/Lower")

        mgr.set_active_program(uid, pid2)
        progs = mgr.list_programs(uid)
        active = [p for p in progs if p["is_active"] == 1]
        assert len(active) == 1
        assert active[0]["id"] == pid2
    finally:
        mgr.close()
