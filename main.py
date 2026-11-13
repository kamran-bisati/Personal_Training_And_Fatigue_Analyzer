"""Phase 1 entry point.

Builds the in-Python sample fitness dataset and prints an inspection report so
we can confirm the data is loadable, understandable and analysable.

Run from the project root:

    python main.py
"""

from __future__ import annotations

import pandas as pd

from database import repository as repo
from database.db_setup import get_connection, reset_db
from src.data.data_cleaning import clean_recovery_logs, clean_workout_sets
from src.data.sample_dataset import load_dataset
from src.data.validation import (
    issues_to_frame,
    validate_recovery_logs,
    validate_workout_sets,
)
from src.management.exercise_manager import ExerciseManager
from src.management.program_manager import ProgramManager
from src.management.workout_manager import WorkoutManager

pd.set_option("display.width", 120)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", 100)


def section(title: str) -> None:
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def inspect_table(name: str, df: pd.DataFrame) -> None:
    section(f"TABLE: {name}")
    print(f"shape: {df.shape[0]} rows x {df.shape[1]} columns")
    print(f"date range: {df['date'].min()} -> {df['date'].max()}")

    print("\ncolumns and dtypes:")
    print(df.dtypes.to_string())

    print("\nfirst rows:")
    print(df.head(6).to_string(index=False))

    print("\nnumeric summary:")
    print(df.describe().round(2).to_string())

    missing = df.isna().sum()
    missing = missing[missing > 0]
    print(f"\nmissing values: {int(df.isna().sum().sum())}")
    if not missing.empty:
        print(missing.to_string())

    print(f"\nduplicate rows: {int(df.duplicated().sum())}")

    categorical = [c for c in df.columns if df[c].dtype == "object" and c != "date"]
    if categorical:
        print("\nunique values per categorical column:")
        for column in categorical:
            values = sorted(df[column].dropna().unique().tolist())
            print(f"  {column} ({len(values)}): {values}")


def show_manipulations(workouts: pd.DataFrame, recovery: pd.DataFrame) -> None:
    section("MANIPULATION 1 - volume and RPE by muscle group")
    workouts = workouts.assign(volume=workouts["sets"] * workouts["reps"] * workouts["weight_kg"])
    by_muscle = (
        workouts.groupby("muscle_group")
        .agg(
            set_records=("exercise", "count"),
            total_sets=("sets", "sum"),
            total_volume_kg=("volume", "sum"),
            avg_rpe=("rpe", "mean"),
        )
        .sort_values("total_volume_kg", ascending=False)
        .round(1)
    )
    print(by_muscle.to_string())

    section("MANIPULATION 2 - weekly training volume and average RPE")
    weekly = (
        workouts.groupby("week")
        .agg(total_volume_kg=("volume", "sum"), avg_rpe=("rpe", "mean"), sessions=("date", "nunique"))
        .round(1)
    )
    weekly["volume_change_pct"] = weekly["total_volume_kg"].pct_change().mul(100).round(1)
    print(weekly.to_string())

    section("MANIPULATION 3 - bench press progression (e1RM preview, Epley)")
    bench = workouts[workouts["exercise"] == "Bench Press"].copy()
    bench["e1rm_kg"] = bench["weight_kg"] * (1 + bench["reps"] / 30)
    print(bench[["date", "week", "weight_kg", "reps", "rpe", "e1rm_kg"]].round(1).to_string(index=False))

    section("MANIPULATION 4 - weekly recovery averages")
    by_week = (
        recovery.groupby("week")
        .agg(
            avg_sleep_h=("sleep_hours", "mean"),
            avg_soreness=("soreness", "mean"),
            avg_energy=("energy", "mean"),
            avg_body_weight_kg=("body_weight_kg", "mean"),
            logged_days=("date", "count"),
        )
        .round(2)
    )
    print(by_week.to_string())

    section("MANIPULATION 5 - heaviest five set records")
    heaviest = workouts.nlargest(5, "weight_kg")[
        ["date", "exercise", "muscle_group", "weight_kg", "reps", "rpe"]
    ]
    print(heaviest.to_string(index=False))


def show_validation(dataset: dict[str, pd.DataFrame]) -> None:
    section("VALIDATION - workout_sets (dirty sample)")
    workout_issues = validate_workout_sets(dataset["workout_sets"])
    errors = sum(1 for i in workout_issues if i.severity == "error")
    warnings = sum(1 for i in workout_issues if i.severity == "warning")
    print(f"{len(workout_issues)} issue(s): {errors} error(s), {warnings} warning(s)")
    print(issues_to_frame(workout_issues).to_string(index=False))

    section("VALIDATION - recovery_logs (dirty sample)")
    recovery_issues = validate_recovery_logs(dataset["recovery_logs"])
    errors = sum(1 for i in recovery_issues if i.severity == "error")
    warnings = sum(1 for i in recovery_issues if i.severity == "warning")
    print(f"{len(recovery_issues)} issue(s): {errors} error(s), {warnings} warning(s)")
    print(issues_to_frame(recovery_issues).to_string(index=False))

    section("CLEANING - workout_sets (missing_strategy='drop')")
    workouts = clean_workout_sets(dataset["workout_sets"], missing_strategy="drop")
    print(workouts.log.summary())
    print("\nrejected rows:")
    print(workouts.rejected.to_string(index=False))

    section("CLEANING - recovery_logs (missing_strategy='drop')")
    recovery = clean_recovery_logs(dataset["recovery_logs"], missing_strategy="drop")
    print(recovery.log.summary())
    print("\nrejected rows:")
    print(recovery.rejected.to_string(index=False))


def show_management() -> None:
    section("PHASE 4 - Workout and exercise management")

    conn = get_connection("database/fitness.db")
    try:
        user_id = repo.create_user(conn, "Demo User", age=30, height_cm=180.0, weight_kg=78.0, goal="strength")

        with ExerciseManager(connection=conn) as ex_mgr:
            print(f"exercises in library: {len(ex_mgr.list_exercises())}")
            chest = ex_mgr.list_exercises(primary_muscle_group="Chest")
            print("chest exercises:", [e["name"] for e in chest])
            groups = ex_mgr.list_muscle_groups()
            print("muscle groups:", groups)

        with WorkoutManager(connection=conn) as wk_mgr:
            session_id = wk_mgr.create_session(user_id, "2026-10-05", duration_min=60)
            bench = repo.get_exercise_by_name(conn, "Bench Press")
            wk_mgr.add_set(session_id, bench["id"], 1, 5, 80.0, 8.0)
            wk_mgr.add_set(session_id, bench["id"], 2, 5, 85.0, 8.5)

            sets = wk_mgr.get_sets_for_session(session_id)
            print(f"\nsession {session_id} has {len(sets)} sets:")
            for s in sets:
                print(f"  {s['exercise_name']}: {s['reps']}x{s['weight_kg']}kg RPE {s['rpe']}")

            history = wk_mgr.workout_history(user_id)
            print(f"\nworkout history: {len(history)} total set records")

            records = wk_mgr.personal_records(user_id, bench["id"])
            print(f"bench press PR: {records['max_weight_kg']}kg x {records['max_reps']} reps")

        with ProgramManager(connection=conn) as pr_mgr:
            pid = pr_mgr.create_from_template(user_id, "PPL Starter", "PPL", template="PPL")
            structure = pr_mgr.get_program_structure(pid)
            day_names = sorted({r["day_name"] for r in structure})
            print(f"\nprogram '{pr_mgr.get_program(pid)['name']}' ({pid}): {len(structure)} assignments across {day_names}")

            ul_pid = pr_mgr.create_from_template(user_id, "Upper/Lower Starter", "Upper/Lower", template="Upper/Lower")
            ul_structure = pr_mgr.get_program_structure(ul_pid)
            ul_days = sorted({r["day_name"] for r in ul_structure})
            print(f"program 'Upper/Lower Starter': {len(ul_structure)} assignments across {ul_days}")

            pr_mgr.set_active_program(user_id, pid)
            active = [p for p in pr_mgr.list_programs(user_id) if p["is_active"] == 1]
            print(f"active program: {active[0]['name']}")
    finally:
        conn.close()


def show_database(dataset: dict[str, pd.DataFrame]) -> None:
    section("PHASE 3 - SQLite database + CRUD layer")

    clean_workouts = clean_workout_sets(dataset["workout_sets"], missing_strategy="drop").data
    clean_recovery = clean_recovery_logs(dataset["recovery_logs"], missing_strategy="drop").data

    conn = reset_db("database/fitness.db")
    try:
        user_id = repo.create_user(conn, "Demo User", age=30, height_cm=180.0, weight_kg=78.0, goal="strength")

        exercise_cache = {
            row["name"]: row["id"] for row in repo.list_exercises(conn)
        }

        sessions_created = 0
        sets_created = 0
        for session_date, group in clean_workouts.groupby("date"):
            date_str = session_date.strftime("%Y-%m-%d")
            duration = int(group["session_duration_min"].iloc[0])
            session_id = repo.create_session(conn, user_id, date_str, duration_min=duration)
            sessions_created += 1
            for set_number, (_, row) in enumerate(group.iterrows(), start=1):
                exercise_id = exercise_cache[row["exercise"]]
                repo.add_set(
                    conn,
                    session_id=session_id,
                    exercise_id=exercise_id,
                    set_number=set_number,
                    reps=int(row["reps"]),
                    weight_kg=float(row["weight_kg"]),
                    rpe=float(row["rpe"]),
                )
                sets_created += 1

        recovery_created = 0
        for _, row in clean_recovery.iterrows():
            date_str = row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"])[:10]
            repo.log_recovery(
                conn,
                user_id,
                date_str,
                sleep_hours=(float(row["sleep_hours"]) if pd.notna(row["sleep_hours"]) else None),
                body_weight_kg=(float(row["body_weight_kg"]) if pd.notna(row["body_weight_kg"]) else None),
                soreness=(int(row["soreness"]) if pd.notna(row["soreness"]) else None),
                energy=(int(row["energy"]) if pd.notna(row["energy"]) else None),
            )
            recovery_created += 1

        session_count = conn.execute("SELECT COUNT(*) AS c FROM workout_sessions").fetchone()["c"]
        set_count = conn.execute("SELECT COUNT(*) AS c FROM workout_sets").fetchone()["c"]
        recovery_count = conn.execute("SELECT COUNT(*) AS c FROM recovery_logs").fetchone()["c"]
        exercise_count = conn.execute("SELECT COUNT(*) AS c FROM exercises").fetchone()["c"]

        print(f"users: 1 | exercises: {exercise_count} | sessions: {sessions_created} | sets: {sets_created} | recovery: {recovery_created}")
        print(f"(tables confirm: sessions={session_count}, sets={set_count}, recovery={recovery_count})")

        section("Sample query - workout history for Demo User (first 6 sets)")
        history = repo.workout_history(conn, user_id)
        print(f"{len(history)} set records joined to sessions and exercises")
        for row in history[:6]:
            print(dict(row))

        section("Sample query - personal records for Bench Press")
        bench = repo.get_exercise_by_name(conn, "Bench Press")
        if bench:
            records = repo.personal_records(conn, user_id, bench["id"])
            for record in records:
                print(dict(record))

    finally:
        conn.close()


def main() -> None:
    dataset = load_dataset()
    workouts = dataset["workout_sets"]
    recovery = dataset["recovery_logs"]

    inspect_table("workout_sets", workouts)
    inspect_table("recovery_logs", recovery)

    section("DATA QUALITY SNAPSHOT (intentional dirty rows)")
    print(f"workout rows with RPE outside 1-10: {int(((workouts['rpe'] < 1) | (workouts['rpe'] > 10)).sum())}")
    print(f"workout rows with reps <= 0:        {int((workouts['reps'] <= 0).sum())}")
    print(f"workout rows with missing weight:   {int(workouts['weight_kg'].isna().sum())}")
    print(f"recovery rows with missing sleep:   {int(recovery['sleep_hours'].isna().sum())}")
    print(f"recovery rows with energy outside 1-10: {int(((recovery['energy'] < 1) | (recovery['energy'] > 10)).sum())}")

    show_validation(dataset)

    show_management()

    show_database(dataset)

    clean = load_dataset(include_anomalies=False)
    show_manipulations(clean["workout_sets"], clean["recovery_logs"])

    section("PHASES 1-3 COMPLETE")
    print("Phase 1: dataset builds in Python and supports pandas analysis.")
    print("Phase 2: input validation flags bad records and the cleaning pipeline")
    print("returns clean data, rejected rows and a log.")
    print("Phase 3: SQLite schema + CRUD layer persists users, exercises,")
    print("sessions, sets, recovery logs and programs locally.")
    print("Next: Phase 4 - workout and exercise management module.")


if __name__ == "__main__":
    main()
