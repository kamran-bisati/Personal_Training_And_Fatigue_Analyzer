"""Reset and seed the database with 3 users (2 test + kamran) and rich, distinct data.

This removes Smoke User (ID 4), Ex User (ID 5), and extra Test User (ID 3),
then wipes and reseeds the kept users so every navigation option can be tested.

Run:
    python reset_and_seed.py
"""

from __future__ import annotations

from datetime import date, timedelta

from database.db_setup import get_connection
from database import repository as repo

DB_PATH = "database/fitness.db"

KEPT_USER_IDS = [1, 2, 6]  # Test User, Test User, kamran


def _wipe_user_data(conn, user_id: int) -> None:
    """Delete all data belonging to a user (sessions cascade to sets)."""
    sessions = repo.list_sessions_by_user(conn, user_id)
    for s in sessions:
        repo.delete_session(conn, s["id"])
    for r in repo.list_recovery_by_user(conn, user_id):
        repo.delete_recovery(conn, r["id"])
    for p in repo.list_programs_by_user(conn, user_id):
        repo.delete_program(conn, p["id"])


def _add_session_sets(
    conn,
    user_id: int,
    exercise_ids: list[int],
    base_date: date,
    duration_min: int,
    reps: int,
    weight_kg: float,
    rpe: float,
) -> int | None:
    existing = repo.list_sessions_by_user(conn, user_id)
    session_date = base_date.isoformat()
    if any(s["session_date"] == session_date for s in existing):
        return None  # already exists

    session_id = repo.create_session(
        conn, user_id, session_date, duration_min=duration_min
    )
    for exercise_id in exercise_ids:
        for set_num in (1, 2, 3):
            repo.add_set(
                conn,
                session_id=session_id,
                exercise_id=exercise_id,
                set_number=set_num,
                reps=reps,
                weight_kg=weight_kg,
                rpe=rpe,
            )
    return session_id


def _add_recovery(
    conn,
    user_id: int,
    base_date: date,
    sleep: float,
    bw,
    soreness: int,
    energy: int,
) -> None:
    log_date = base_date.isoformat()
    repo.log_recovery(
        conn,
        user_id=user_id,
        log_date=log_date,
        sleep_hours=sleep,
        body_weight_kg=bw,
        soreness=soreness,
        energy=energy,
    )


def _create_program(
    conn,
    user_id: int,
    name: str,
    split_type: str,
    days_exercises: dict,
) -> int:
    pid = repo.create_program(
        conn, user_id=user_id, name=name, split_type=split_type, is_active=1
    )
    for day_order, (day_name, exercises) in enumerate(
        days_exercises.items(), start=1
    ):
        day_id = repo.create_program_day(
            conn, program_id=pid, day_name=day_name, day_order=day_order
        )
        for ex_name, sets_, reps_, weight in exercises:
            ex = repo.get_exercise_by_name(conn, ex_name)
            if ex is None:
                continue
            repo.add_program_exercise(
                conn,
                program_day_id=day_id,
                exercise_id=ex["id"],
                target_sets=sets_,
                target_reps=reps_,
                target_weight_kg=weight,
            )
    return pid


def main() -> None:
    conn = get_connection(DB_PATH)
    try:
        # --- Remove unwanted users ---
        all_users = repo.list_users(conn)
        for u in all_users:
            if u["id"] not in KEPT_USER_IDS:
                _wipe_user_data(conn, u["id"])
                repo.delete_user(conn, u["id"])
                print(f"Removed user {u['id']} ({u['name']})")

        # --- Wipe data for kept users ---
        for uid in KEPT_USER_IDS:
            _wipe_user_data(conn, uid)
        conn.commit()

        # Resolve exercises we will reference
        bench = repo.get_exercise_by_name(conn, "Bench Press")
        squat = repo.get_exercise_by_name(conn, "Back Squat")
        deadlift = repo.get_exercise_by_name(conn, "Deadlift")
        row = repo.get_exercise_by_name(conn, "Barbell Row")
        press = repo.get_exercise_by_name(conn, "Overhead Press")
        curl = repo.get_exercise_by_name(conn, "Biceps Curl")
        pushdown = repo.get_exercise_by_name(conn, "Triceps Pushdown")
        pulldown = repo.get_exercise_by_name(conn, "Pull-Up")
        legpress = repo.get_exercise_by_name(conn, "Leg Press")
        rdl = repo.get_exercise_by_name(conn, "Romanian Deadlift")

        # =================================================================
        # USER 1: Test User (ID 1) — Strength focus
        # Heavy compound lifts, low reps, high RPE
        # =================================================================
        uid = 1
        base = date(2026, 11, 1)
        for i, (exercise_ids, reps, weight, rpe) in enumerate([
            ([bench["id"], press["id"], curl["id"]], 5, 100.0, 8.5),
            ([squat["id"], deadlift["id"], rdl["id"]], 5, 140.0, 9.0),
            ([bench["id"], row["id"], pushdown["id"]], 5, 105.0, 8.0),
        ]):
            _add_session_sets(
                conn, uid, exercise_ids, base + timedelta(days=i * 7),
                duration_min=75, reps=reps, weight_kg=weight, rpe=rpe,
            )

        for i in range(4):
            _add_recovery(
                conn, uid, base + timedelta(days=i),
                sleep=6.5 + i * 0.2, bw=80.0 + i * 0.3,
                soreness=7 - i, energy=5 + i,
            )

        _create_program(
            conn, uid, "Strength Base", "PPL",
            {
                "Push": [("Bench Press", 4, 5, 100.0), ("Overhead Press", 3, 8, 50.0), ("Triceps Pushdown", 3, 12, 30.0)],
                "Pull": [("Deadlift", 3, 5, 140.0), ("Barbell Row", 4, 8, 75.0), ("Pull-Up", 3, 8, 0.0)],
                "Legs": [("Back Squat", 4, 5, 140.0), ("Romanian Deadlift", 3, 8, 90.0), ("Leg Press", 3, 12, 150.0)],
            },
        )

        # =================================================================
        # USER 2: Test User (ID 2) — Hypertrophy focus
        # Higher reps, moderate weight, bodyweight + machines
        # =================================================================
        uid = 2
        base = date(2026, 11, 3)
        for i, (exercise_ids, reps, weight, rpe) in enumerate([
            ([curl["id"], pushdown["id"], legpress["id"]], 12, 20.0, 7.0),
            ([bench["id"], row["id"], pulldown["id"]], 10, 80.0, 7.5),
            ([squat["id"], rdl["id"], legpress["id"]], 12, 100.0, 7.0),
        ]):
            _add_session_sets(
                conn, uid, exercise_ids, base + timedelta(days=i * 7),
                duration_min=60, reps=reps, weight_kg=weight, rpe=rpe,
            )

        for i in range(4):
            _add_recovery(
                conn, uid, base + timedelta(days=i),
                sleep=8.0 - i * 0.1, bw=70.0 + i * 0.2,
                soreness=4 + i, energy=8 - i,
            )

        _create_program(
            conn, uid, "Hypertrophy Split", "Upper/Lower",
            {
                "Upper A": [("Bench Press", 4, 10, 80.0), ("Barbell Row", 4, 10, 70.0), ("Biceps Curl", 3, 12, 15.0), ("Triceps Pushdown", 3, 12, 25.0)],
                "Lower A": [("Back Squat", 4, 10, 100.0), ("Romanian Deadlift", 3, 10, 80.0), ("Leg Press", 3, 12, 140.0), ("Pull-Up", 3, 8, 0.0)],
                "Upper B": [("Overhead Press", 4, 10, 45.0), ("Barbell Row", 3, 12, 60.0), ("Biceps Curl", 3, 15, 12.0), ("Triceps Pushdown", 4, 15, 20.0)],
                "Lower B": [("Back Squat", 3, 12, 90.0), ("Deadlift", 3, 8, 120.0), ("Leg Press", 4, 15, 130.0), ("Pull-Up", 3, 10, 0.0)],
            },
        )

        # =================================================================
        # USER 6: kamran — Mixed / Full Body focus
        # Varied exercises, mixed rep ranges
        # =================================================================
        uid = 6
        base = date(2026, 11, 5)
        for i, (exercise_ids, reps, weight, rpe) in enumerate([
            ([bench["id"], squat["id"], press["id"]], 8, 90.0, 7.5),
            ([deadlift["id"], row["id"], pulldown["id"]], 6, 110.0, 8.0),
            ([legpress["id"], curl["id"], pushdown["id"]], 15, 40.0, 6.5),
            ([bench["id"], squat["id"], deadlift["id"]], 5, 120.0, 9.0),
        ]):
            _add_session_sets(
                conn, uid, exercise_ids, base + timedelta(days=i * 5),
                duration_min=90, reps=reps, weight_kg=weight, rpe=rpe,
            )

        for i in range(5):
            _add_recovery(
                conn, uid, base + timedelta(days=i),
                sleep=7.0 + i * 0.15, bw=75.0 + i * 0.4,
                soreness=5 - (i % 3), energy=7 - (i % 2),
            )

        _create_program(
            conn, uid, "Full Body Balanced", "Full Body",
            {
                "Full Body A": [("Bench Press", 3, 8, 90.0), ("Back Squat", 3, 8, 110.0), ("Barbell Row", 3, 8, 75.0)],
                "Full Body B": [("Overhead Press", 3, 10, 50.0), ("Deadlift", 3, 6, 130.0), ("Leg Press", 3, 12, 160.0)],
            },
        )

        conn.commit()
        print("\nSeeding complete. Summary:")
        for kept_uid in KEPT_USER_IDS:
            u = repo.get_user(conn, kept_uid)
            sessions = repo.list_sessions_by_user(conn, kept_uid)
            recovery = repo.list_recovery_by_user(conn, kept_uid)
            programs = repo.list_programs_by_user(conn, kept_uid)
            print(
                f"  User {kept_uid} ({u['name']}): "
                f"{len(sessions)} session(s), {len(recovery)} recovery log(s), "
                f"{len(programs)} program(s)"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
