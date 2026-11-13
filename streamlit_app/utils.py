"""Utility helpers for loading SQLite data into pandas DataFrames for the
analytics, metrics, detection and reporting modules."""

from __future__ import annotations

import pandas as pd

from database import repository as repo


def load_workout_df(conn, user_id: int) -> pd.DataFrame:
    """Load a user's workout history as a DataFrame ready for analytics.

    Adds a ``sets = 1`` column (each DB row is one set) and renames
    ``session_date`` → ``date`` and ``exercise_name`` → ``exercise`` so the
    DataFrame matches the schema expected by the metrics/detection modules.
    """
    rows = repo.workout_history(conn, user_id)
    if not rows:
        return pd.DataFrame(
            columns=[
                "date", "exercise", "muscle_group", "equipment",
                "sets", "reps", "weight_kg", "rpe",
            ]
        )
    df = pd.DataFrame([dict(r) for r in rows])
    df = df.rename(
        columns={
            "session_date": "date",
            "exercise_name": "exercise",
            "primary_muscle_group": "muscle_group",
        }
    )
    df["sets"] = 1  # each row is one set
    df["date"] = pd.to_datetime(df["date"])
    return df[
        ["date", "exercise", "muscle_group", "equipment", "sets", "reps", "weight_kg", "rpe"]
    ]


def load_recovery_df(conn, user_id: int) -> pd.DataFrame:
    """Load a user's recovery logs as a DataFrame ready for analytics."""
    rows = repo.list_recovery_by_user(conn, user_id)
    if not rows:
        return pd.DataFrame(
            columns=["date", "sleep_hours", "body_weight_kg", "soreness", "energy"]
        )
    df = pd.DataFrame([dict(r) for r in rows])
    df["date"] = pd.to_datetime(df["date"])
    return df[["date", "sleep_hours", "body_weight_kg", "soreness", "energy"]]


def load_sessions_df(conn, user_id: int) -> pd.DataFrame:
    """Load a user's workout sessions as a DataFrame."""
    rows = repo.list_sessions_by_user(conn, user_id)
    if not rows:
        return pd.DataFrame(columns=["id", "session_date", "duration_min", "notes"])
    df = pd.DataFrame([dict(r) for r in rows])
    df["session_date"] = pd.to_datetime(df["session_date"])
    return df[["id", "session_date", "duration_min", "notes"]]
