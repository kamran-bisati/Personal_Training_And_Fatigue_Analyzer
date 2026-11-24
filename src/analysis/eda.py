"""Exploratory data analysis for workout and recovery records.

Phase 5 deliverable. Every function is pure: it takes a DataFrame and returns
a new DataFrame or dict. Nothing is modified in place and nothing is raised.

Designed to work with the sample dataset from ``src.data.sample_dataset`` as
well as with DataFrames loaded from SQLite (same column names).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

VolumePeriod = Literal["week", "month"]


@dataclass(frozen=True)
class EDAResult:
    """Container for a single EDA finding."""

    metric: str
    value: object
    interpretation: str


def _ensure_date_column(df: pd.DataFrame, column: str = "date") -> pd.DataFrame:
    """Return a copy with ``column`` parsed to datetime64 (invalid -> NaT)."""
    result = df.copy()
    if column in result.columns:
        result[column] = pd.to_datetime(result[column], errors="coerce")
    return result


def _add_volume_column(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with a ``volume_kg`` column (sets × reps × weight_kg)."""
    result = df.copy()
    required = {"sets", "reps", "weight_kg"}
    if required.issubset(result.columns):
        result["volume_kg"] = (
            result["sets"].astype(float)
            * result["reps"].astype(float)
            * result["weight_kg"].astype(float)
        )
    return result


# ------------------------------------------------------------------ frequency


def workout_frequency(
    df: pd.DataFrame, period: VolumePeriod = "week"
) -> pd.DataFrame:
    """Count distinct workout sessions per period.

    Uses the ``date`` column. ``session_duration_min`` is repeated on every
    set row of a session (it belongs to the session, not the set), so we count
    distinct dates rather than summing duration.
    """
    working = _ensure_date_column(df)
    if "date" not in working.columns:
        return pd.DataFrame(columns=["period", "sessions"])

    working = working.dropna(subset=["date"]).copy()
    if period == "week":
        working["period"] = working["date"].dt.to_period("W").astype(str)
    else:
        working["period"] = working["date"].dt.to_period("M").astype(str)

    sessions = working.groupby("period")["date"].nunique().reset_index()
    sessions.columns = ["period", "sessions"]
    sessions = sessions.sort_values("period").reset_index(drop=True)
    return sessions


def exercise_frequency(df: pd.DataFrame) -> pd.DataFrame:
    """Count how often each exercise appears (set records)."""
    if "exercise" not in df.columns:
        return pd.DataFrame(columns=["exercise", "set_records"])

    freq = (
        df.groupby("exercise")
        .size()
        .reset_index(name="set_records")
        .sort_values("set_records", ascending=False)
        .reset_index(drop=True)
    )
    return freq


# ---------------------------------------------------------------- volume / workload


def training_volume_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Total training volume per period (week), with period-over-period change.

    Volume = sets × reps × weight_kg per set row, summed across the period.
    """
    working = _ensure_date_column(df)
    working = _add_volume_column(working)
    if "volume_kg" not in working.columns or "date" not in working.columns:
        return pd.DataFrame(columns=["week", "total_volume_kg", "volume_change_pct"])

    working = working.dropna(subset=["date", "volume_kg"]).copy()
    working["week"] = working["date"].dt.to_period("W").astype(str)

    weekly = (
        working.groupby("week")["volume_kg"]
        .sum()
        .reset_index(name="total_volume_kg")
        .sort_values("week")
        .reset_index(drop=True)
    )
    weekly["volume_change_pct"] = weekly["total_volume_kg"].pct_change().mul(100).round(1)
    return weekly


def muscle_group_workload(df: pd.DataFrame) -> pd.DataFrame:
    """Distribution of training volume by muscle group."""
    working = _add_volume_column(df)
    if "volume_kg" not in working.columns or "muscle_group" not in working.columns:
        return pd.DataFrame(columns=["muscle_group", "total_volume_kg", "share_pct"])

    working = working.dropna(subset=["volume_kg", "muscle_group"]).copy()
    total = working["volume_kg"].sum()

    by_muscle = (
        working.groupby("muscle_group")["volume_kg"]
        .sum()
        .reset_index(name="total_volume_kg")
        .sort_values("total_volume_kg", ascending=False)
        .reset_index(drop=True)
    )
    if total > 0:
        by_muscle["share_pct"] = (by_muscle["total_volume_kg"] / total * 100).round(1)
    else:
        by_muscle["share_pct"] = 0.0
    return by_muscle


# ------------------------------------------------------------------ RPE


def average_rpe(df: pd.DataFrame, by: Literal["week", "session"] = "week") -> pd.DataFrame:
    """Mean RPE, grouped by week or by session date."""
    if "rpe" not in df.columns:
        return pd.DataFrame(columns=["period", "avg_rpe", "n_records"])

    working = df.dropna(subset=["rpe"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["period", "avg_rpe", "n_records"])

    if by == "week":
        working = _ensure_date_column(working)
        working = working.dropna(subset=["date"]).copy()
        working["period"] = working["date"].dt.to_period("W").astype(str)
    else:
        working = _ensure_date_column(working)
        working = working.dropna(subset=["date"]).copy()
        working["period"] = working["date"].dt.strftime("%Y-%m-%d")

    result = (
        working.groupby("period")
        .agg(avg_rpe=("rpe", "mean"), n_records=("rpe", "size"))
        .round(2)
        .reset_index()
        .sort_values("period")
        .reset_index(drop=True)
    )
    return result


# ---------------------------------------------------------------- recovery


def sleep_patterns(df: pd.DataFrame, by: Literal["day", "week"] = "week") -> pd.DataFrame:
    """Daily or weekly sleep averages with day-type breakdown when available."""
    if "sleep_hours" not in df.columns:
        return pd.DataFrame(columns=["period", "avg_sleep_h", "n_days"])

    working = _ensure_date_column(df)
    working = working.dropna(subset=["date", "sleep_hours"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["period", "avg_sleep_h", "n_days"])

    if by == "week":
        working["period"] = working["date"].dt.to_period("W").astype(str)
    else:
        working["period"] = working["date"].dt.strftime("%Y-%m-%d")

    agg: dict[str, str] = {"avg_sleep_h": "sleep_hours", "n_days": "sleep_hours"}
    result = (
        working.groupby("period")["sleep_hours"]
        .agg(["mean", "size"])
        .round(2)
        .rename(columns={"mean": "avg_sleep_h", "size": "n_days"})
        .reset_index()
        .sort_values("period")
        .reset_index(drop=True)
    )
    return result


def body_weight_changes(df: pd.DataFrame) -> pd.DataFrame:
    """Day-to-day body-weight change (current minus previous measurement)."""
    if "body_weight_kg" not in df.columns or "date" not in df.columns:
        return pd.DataFrame(columns=["date", "body_weight_kg", "change_kg"])

    working = _ensure_date_column(df)
    working = working.dropna(subset=["date", "body_weight_kg"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["date", "body_weight_kg", "change_kg"])

    working = working.sort_values("date").reset_index(drop=True)
    working["change_kg"] = working["body_weight_kg"].diff().round(2)
    return working[["date", "body_weight_kg", "change_kg"]]


# ----------------------------------------------------------- recovery vs performance


def recovery_vs_performance(
    workout_df: pd.DataFrame, recovery_df: pd.DataFrame
) -> pd.DataFrame:
    """Join weekly recovery averages with weekly average RPE and volume.

    Returns one row per week with sleep, soreness, energy, avg RPE, and total
    volume so the relationship between recovery and performance can be inspected.
    """
    workout = _ensure_date_column(workout_df)
    workout = _add_volume_column(workout)
    workout = workout.dropna(subset=["date"]).copy()

    recovery = _ensure_date_column(recovery_df)
    recovery = recovery.dropna(subset=["date"]).copy()

    if workout.empty or recovery.empty:
        return pd.DataFrame(
            columns=[
                "week",
                "avg_sleep_h",
                "avg_soreness",
                "avg_energy",
                "avg_rpe",
                "total_volume_kg",
            ]
        )

    # Weekly recovery averages
    recovery["week"] = recovery["date"].dt.to_period("W").astype(str)
    weekly_recovery = (
        recovery.groupby("week")
        .agg(
            avg_sleep_h=("sleep_hours", "mean"),
            avg_soreness=("soreness", "mean"),
            avg_energy=("energy", "mean"),
        )
        .round(2)
    )

    # Weekly performance aggregates
    workout["week"] = workout["date"].dt.to_period("W").astype(str)
    weekly_perf = workout.groupby("week").agg(
        avg_rpe=("rpe", "mean"),
        total_volume_kg=("volume_kg", "sum"),
    )
    if "volume_kg" not in workout.columns:
        weekly_perf["total_volume_kg"] = np.nan

    combined = weekly_recovery.join(weekly_perf, how="outer").reset_index()
    combined = combined.sort_values("week").reset_index(drop=True)
    return combined


# ---------------------------------------------------------------- summary report


def summary_report(
    workout_df: pd.DataFrame, recovery_df: pd.DataFrame
) -> dict[str, object]:
    """Produce a compact dictionary of headline EDA findings."""
    report: dict[str, object] = {}

    # Workout frequency
    freq = workout_frequency(workout_df)
    report["workout_frequency"] = freq
    report["total_sessions"] = int(freq["sessions"].sum()) if not freq.empty else 0

    # Exercise frequency
    report["exercise_frequency"] = exercise_frequency(workout_df)

    # Volume
    volume = training_volume_distribution(workout_df)
    report["training_volume_by_week"] = volume
    if not volume.empty:
        report["total_volume_kg"] = float(volume["total_volume_kg"].sum())
        report["avg_weekly_volume_kg"] = float(volume["total_volume_kg"].mean())
    else:
        report["total_volume_kg"] = 0.0
        report["avg_weekly_volume_kg"] = 0.0

    # Muscle workload
    report["muscle_group_workload"] = muscle_group_workload(workout_df)

    # RPE
    rpe = average_rpe(workout_df, by="week")
    report["average_rpe_by_week"] = rpe
    if not rpe.empty:
        report["overall_avg_rpe"] = float(rpe["avg_rpe"].mean())
    else:
        report["overall_avg_rpe"] = None

    # Recovery
    sleep = sleep_patterns(recovery_df, by="week")
    report["sleep_by_week"] = sleep
    if not sleep.empty:
        report["overall_avg_sleep_h"] = float(sleep["avg_sleep_h"].mean())
    else:
        report["overall_avg_sleep_h"] = None

    # Body weight
    bw = body_weight_changes(recovery_df)
    report["body_weight_changes"] = bw
    if not bw.empty and bw["change_kg"].notna().any():
        report["latest_body_weight_kg"] = float(bw["body_weight_kg"].iloc[-1])
        report["total_body_weight_change_kg"] = float(bw["change_kg"].sum())
    else:
        report["latest_body_weight_kg"] = None
        report["total_body_weight_change_kg"] = None

    # Recovery vs performance
    report["recovery_vs_performance"] = recovery_vs_performance(workout_df, recovery_df)

    return report
