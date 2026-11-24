"""Seed sample data into the existing database so you can test all pages.

Run from the project root:

    python seed_demo_data.py

This is additive only — it does not delete or reset anything.
"""

from __future__ import annotations

from datetime import date, timedelta

from database.db_setup import get_connection
from database import repository as repo

DB_PATH = "database/fitness.db"


def _add_session_sets(conn, user_id: int, exercise_ids: list[int], base_date: date) -> None:
    """Create one session with 3 sets for each exercise on base_date."""
    session_date = base_date.isoformat()
    # Skip if a session already exists this date for this user.
    existing = repo.list_sessions_by_user(conn, user_id)
    if any(s["session_date"] == session_date for s in existing):
        return

    session_id = repo.create_session(conn, user_id, session_date, duration_min=60)
    for exercise_id in exercise_ids:
        for set_num in (1, 2, 3):
            repo.add_set(
                conn,
                session_id=session_id,
                exercise_id=exercise_id,
                set_number=set_num,
                reps=8,
                weight_kg=60.0 + exercise_id * 5.0,
                rpe=7.5,
            )


def _add_recovery(conn, user_id: int, base_date: date, sleep: float, bw, soreness: int, energy: int) -> None:
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


def main() -> None:
    conn = get_connection(DB_PATH)
    try:
        bench = repo.get_exercise_by_name(conn, "Bench Press")
        squat = repo.get_exercise_by_name(conn, "Back Squat")
        row = repo.get_exercise_by_name(conn, "Barbell Row")
        press = repo.get_exercise_by_name(conn, "Overhead Press")

        if not all([bench, squat, row, press]):
            print("Missing seed exercises. Aborting.")
            return

        exercise_ids = [bench["id"], squat["id"], row["id"], press["id"]]

        users = repo.list_users(conn)
        if not users:
            print("No users found. Aborting.")
            return

        # Give each user 3 workout days and 3 recovery days over ~2 weeks.
        for user in users:
            uid = user["id"]
            start = date(2026, 11, 1)

            for offset in (0, 7, 14):
                workout_day = start + timedelta(days=offset)
                _add_session_sets(conn, uid, exercise_ids, workout_day)

            for offset in (0, 1, 2):
                rec_day = start + timedelta(days=offset)
                _add_recovery(
                    conn,
                    uid,
                    rec_day,
                    sleep=7.5 - offset * 0.3,
                    bw=78.0 + offset * 0.5,
                    soreness=3 + offset,
                    energy=8 - offset,
                )

        conn.commit()
        print("Seed data added successfully.")

        # Show summary
        for user in users:
            uid = user["id"]
            sessions = repo.list_sessions_by_user(conn, uid)
            recovery = repo.list_recovery_by_user(conn, uid)
            history = repo.workout_history(conn, uid)
            print(
                f"User {uid} ({user['name']}): "
                f"{len(sessions)} session(s), {len(history)} set(s), "
                f"{len(recovery)} recovery log(s)"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
