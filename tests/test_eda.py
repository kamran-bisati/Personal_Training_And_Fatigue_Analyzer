"""Tests for the Phase 5 EDA module."""

from __future__ import annotations

import pandas as pd
import pytest

from src.analysis.eda import (
    EDAResult,
    average_rpe,
    body_weight_changes,
    exercise_frequency,
    muscle_group_workload,
    recovery_vs_performance,
    sleep_patterns,
    summary_report,
    training_volume_distribution,
    workout_frequency,
)
from src.data.sample_dataset import load_dataset


@pytest.fixture
def workout_df() -> pd.DataFrame:
    return load_dataset(include_anomalies=False)["workout_sets"]


@pytest.fixture
def recovery_df() -> pd.DataFrame:
    return load_dataset(include_anomalies=False)["recovery_logs"]


# ------------------------------------------------------------------ frequency


def test_workout_frequency_returns_sessions_per_week(workout_df):
    result = workout_frequency(workout_df, period="week")
    assert list(result.columns) == ["period", "sessions"]
    assert len(result) == 5  # five weeks
    assert result["sessions"].sum() == 20  # 4 sessions per week


def test_workout_frequency_handles_missing_date_column():
    df = pd.DataFrame({"exercise": ["Bench Press"], "sets": [3]})
    result = workout_frequency(df, period="week")
    assert result.empty


def test_exercise_frequency_counts_set_records(workout_df):
    result = exercise_frequency(workout_df)
    assert list(result.columns) == ["exercise", "set_records"]
    assert result["set_records"].sum() == len(workout_df)
    assert result["set_records"].iloc[0] >= result["set_records"].iloc[-1]  # sorted desc


def test_exercise_frequency_handles_missing_column():
    df = pd.DataFrame({"date": ["2026-01-01"]})
    result = exercise_frequency(df)
    assert result.empty


# ---------------------------------------------------------------- volume / workload


def test_training_volume_distribution_has_change_column(workout_df):
    result = training_volume_distribution(workout_df)
    assert list(result.columns) == ["week", "total_volume_kg", "volume_change_pct"]
    assert len(result) == 5
    # First week has no previous week, so change should be NaN
    assert pd.isna(result["volume_change_pct"].iloc[0])


def test_muscle_group_workload_sums_to_total(workout_df):
    result = muscle_group_workload(workout_df)
    assert list(result.columns) == ["muscle_group", "total_volume_kg", "share_pct"]
    assert abs(result["share_pct"].sum() - 100.0) < 0.1


# ------------------------------------------------------------------ RPE


def test_average_rpe_by_week(workout_df):
    result = average_rpe(workout_df, by="week")
    assert list(result.columns) == ["period", "avg_rpe", "n_records"]
    assert len(result) == 5
    assert (result["avg_rpe"] > 0).all()


def test_average_rpe_by_session(workout_df):
    result = average_rpe(workout_df, by="session")
    assert list(result.columns) == ["period", "avg_rpe", "n_records"]


def test_average_rpe_handles_missing_column():
    df = pd.DataFrame({"date": ["2026-01-01"]})
    result = average_rpe(df, by="week")
    assert result.empty


# ---------------------------------------------------------------- recovery


def test_sleep_patterns_by_week(recovery_df):
    result = sleep_patterns(recovery_df, by="week")
    assert list(result.columns) == ["period", "avg_sleep_h", "n_days"]
    assert len(result) == 5


def test_sleep_patterns_by_day(recovery_df):
    result = sleep_patterns(recovery_df, by="day")
    assert list(result.columns) == ["period", "avg_sleep_h", "n_days"]
    assert len(result) == 35  # one row per calendar day


def test_body_weight_changes(recovery_df):
    result = body_weight_changes(recovery_df)
    assert list(result.columns) == ["date", "body_weight_kg", "change_kg"]
    assert len(result) == 35
    # First row has no previous measurement
    assert pd.isna(result["change_kg"].iloc[0])


# ----------------------------------------------------------- recovery vs performance


def test_recovery_vs_performance_joins_weekly(workout_df, recovery_df):
    result = recovery_vs_performance(workout_df, recovery_df)
    expected_columns = [
        "week",
        "avg_sleep_h",
        "avg_soreness",
        "avg_energy",
        "avg_rpe",
        "total_volume_kg",
    ]
    assert list(result.columns) == expected_columns
    assert len(result) == 5


# ---------------------------------------------------------------- summary report


def test_summary_report_contains_headline_metrics(workout_df, recovery_df):
    report = summary_report(workout_df, recovery_df)
    assert "total_sessions" in report
    assert "total_volume_kg" in report
    assert "avg_weekly_volume_kg" in report
    assert "overall_avg_rpe" in report
    assert "overall_avg_sleep_h" in report
    assert isinstance(report["workout_frequency"], pd.DataFrame)
    assert isinstance(report["exercise_frequency"], pd.DataFrame)


def test_summary_report_on_empty_dataframes():
    empty_workout = pd.DataFrame(
        columns=["date", "exercise", "sets", "reps", "weight_kg", "rpe"]
    )
    empty_recovery = pd.DataFrame(
        columns=["date", "sleep_hours", "body_weight_kg", "soreness", "energy"]
    )
    report = summary_report(empty_workout, empty_recovery)
    assert report["total_sessions"] == 0
    assert report["total_volume_kg"] == 0.0
