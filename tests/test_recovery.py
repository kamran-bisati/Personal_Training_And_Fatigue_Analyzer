"""Tests for the Phase 7 Recovery Analysis Engine."""

from __future__ import annotations

import pandas as pd
import pytest

from src.analysis.recovery import (
    recovery_daily_averages,
    recovery_period_changes,
    recovery_performance_correlation,
    recovery_rolling_averages,
    recovery_summary_report,
    recovery_weekly_averages,
    sleep_consistency,
)
from src.data.sample_dataset import load_dataset


@pytest.fixture
def recovery_df() -> pd.DataFrame:
    return load_dataset(include_anomalies=False)["recovery_logs"]


@pytest.fixture
def workout_df() -> pd.DataFrame:
    return load_dataset(include_anomalies=False)["workout_sets"]


# ------------------------------------------------------------------ daily averages


def test_recovery_daily_averages(recovery_df):
    result = recovery_daily_averages(recovery_df)
    expected_columns = [
        "date",
        "avg_sleep_h",
        "avg_soreness",
        "avg_energy",
        "avg_body_weight_kg",
        "n_records",
    ]
    assert list(result.columns) == expected_columns
    assert len(result) == 35  # one row per calendar day
    assert (result["n_records"] == 1).all()


def test_recovery_daily_averages_missing_column():
    df = pd.DataFrame({"date": ["2026-01-01"], "sleep_hours": [7.0]})
    with pytest.raises(ValueError, match="missing required column"):
        recovery_daily_averages(df)


def test_recovery_daily_averages_non_numeric():
    df = pd.DataFrame(
        {
            "date": ["2026-01-01"],
            "sleep_hours": ["seven"],
            "soreness": [3.0],
            "energy": [8.0],
            "body_weight_kg": [78.0],
        }
    )
    with pytest.raises(TypeError, match="must be numeric"):
        recovery_daily_averages(df)


# ------------------------------------------------------------------ weekly averages


def test_recovery_weekly_averages(recovery_df):
    result = recovery_weekly_averages(recovery_df)
    assert list(result.columns) == [
        "week",
        "avg_sleep_h",
        "avg_soreness",
        "avg_energy",
        "avg_body_weight_kg",
        "n_days",
    ]
    assert len(result) == 5  # five weeks


# ------------------------------------------------------------------ rolling averages


def test_recovery_rolling_averages(recovery_df):
    result = recovery_rolling_averages(recovery_df, window=7)
    assert "roll_sleep_h" in result.columns
    assert "roll_soreness" in result.columns
    assert "roll_energy" in result.columns
    assert "roll_body_weight_kg" in result.columns
    assert len(result) == 35


def test_recovery_rolling_averages_invalid_window(recovery_df):
    with pytest.raises(ValueError, match="window must be >= 1"):
        recovery_rolling_averages(recovery_df, window=0)


# ------------------------------------------------------------------ period changes


def test_recovery_period_changes(recovery_df):
    result = recovery_period_changes(recovery_df, period="week")
    assert "sleep_change" in result.columns
    assert "soreness_change" in result.columns
    assert "energy_change" in result.columns
    assert "body_weight_change" in result.columns
    assert len(result) == 5
    # First period has no previous period -> NaN change
    assert pd.isna(result["sleep_change"].iloc[0])


# ------------------------------------------------------------------ sleep consistency


def test_sleep_consistency(recovery_df):
    result = sleep_consistency(recovery_df, group_by="week")
    assert list(result.columns) == [
        "period",
        "std_sleep_h",
        "range_sleep_h",
        "n_days",
    ]
    assert len(result) == 5
    assert (result["std_sleep_h"] >= 0).all()


# ------------------------------------------------------------------ recovery vs performance correlation


def test_recovery_performance_correlation(workout_df, recovery_df):
    result = recovery_performance_correlation(
        recovery_df, workout_df, "sleep_hours", "rpe"
    )
    assert "correlation" in result
    assert "n_overlapping_days" in result
    assert result["method"] == "pearson"
    assert result["n_overlapping_days"] > 0


def test_recovery_performance_correlation_spearman(workout_df, recovery_df):
    result = recovery_performance_correlation(
        recovery_df, workout_df, "sleep_hours", "rpe", method="spearman"
    )
    assert result["method"] == "spearman"


def test_recovery_performance_correlation_insufficient_data():
    recovery = pd.DataFrame(
        {"date": ["2026-01-01"], "sleep_hours": [7.0]}
    )
    workout = pd.DataFrame(
        {"date": ["2026-01-01"], "rpe": [8.0]}
    )
    result = recovery_performance_correlation(recovery, workout, "sleep_hours", "rpe")
    assert result["correlation"] is None
    assert result["n_overlapping_days"] == 1


def test_recovery_performance_correlation_missing_column(workout_df, recovery_df):
    with pytest.raises(ValueError, match="missing required column"):
        recovery_performance_correlation(
            recovery_df, workout_df, "nonexistent", "rpe"
        )


# ------------------------------------------------------------------ summary report


def test_recovery_summary_report(recovery_df, workout_df):
    report = recovery_summary_report(recovery_df, workout_df)
    assert "weekly_averages" in report
    assert "sleep_consistency" in report
    assert "period_changes" in report
    assert "correlations" in report
    assert isinstance(report["weekly_averages"], pd.DataFrame)
    assert isinstance(report["sleep_consistency"], pd.DataFrame)


def test_recovery_summary_report_without_workout(recovery_df):
    report = recovery_summary_report(recovery_df)
    assert "correlations" not in report


def test_recovery_summary_report_empty_workout(recovery_df):
    empty_workout = pd.DataFrame(
        columns=["date", "exercise", "sets", "reps", "weight_kg", "rpe"]
    )
    report = recovery_summary_report(recovery_df, empty_workout)
    assert "correlations" not in report
