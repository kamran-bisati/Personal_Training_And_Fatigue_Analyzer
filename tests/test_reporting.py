"""Tests for the Phase 9 Reporting and Visualization Engine."""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import pandas as pd
import pytest

from src.reporting.report_generator import (
    daily_summary_report,
    detection_alerts_report,
    monthly_report,
    weekly_report,
)
from src.reporting.visualization import (
    body_weight_chart,
    export_figure_to_png,
    muscle_workload_chart,
    rpe_chart,
    sleep_chart,
    strength_progression_chart,
    weekly_volume_chart,
)


# ------------------------------------------------------------------ fixtures


@pytest.fixture
def workout_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-10-05", "2026-10-05", "2026-10-05",
                    "2026-10-07", "2026-10-07",
                    "2026-10-12", "2026-10-12",
                ]
            ),
            "exercise": [
                "Bench Press", "Bench Press", "Overhead Press",
                "Back Squat", "Back Squat",
                "Bench Press", "Bench Press",
            ],
            "muscle_group": [
                "Chest", "Chest", "Shoulders",
                "Legs", "Legs",
                "Chest", "Chest",
            ],
            "sets": [3, 3, 3, 4, 4, 3, 3],
            "reps": [5, 5, 8, 8, 8, 5, 5],
            "weight_kg": [80.0, 85.0, 45.0, 110.0, 115.0, 85.0, 90.0],
            "rpe": [7.0, 7.5, 7.0, 8.0, 8.0, 7.5, 8.0],
            "session_duration_min": [60, 60, 45, 70, 70, 65, 65],
        }
    )


@pytest.fixture
def recovery_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-12"]
            ),
            "sleep_hours": [7.5, 6.5, 8.0, 6.0],
            "soreness": [3, 4, 2, 5],
            "energy": [8, 6, 9, 5],
            "body_weight_kg": [78.0, 78.2, 77.9, 78.1],
        }
    )


# ------------------------------------------------------------------ visualization tests


def test_strength_progression_chart_returns_figure(workout_df):
    # Add e1rm column
    df = workout_df.copy()
    df["e1rm_kg"] = df["weight_kg"] * (1 + df["reps"] / 30)
    fig = strength_progression_chart(df, exercise_name="Bench Press")
    assert fig is not None
    assert len(fig.axes) == 1


def test_strength_progression_chart_insufficient_data():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-10-05"]),
            "exercise": ["Bench Press"],
            "e1rm_kg": [100.0],
        }
    )
    fig = strength_progression_chart(df, exercise_name="Bench Press")
    assert fig is not None
    # Should show insufficient data message
    ax = fig.axes[0]
    texts = [t.get_text() for t in ax.texts]
    assert any("Insufficient data" in t for t in texts)


def test_weekly_volume_chart_returns_figure(workout_df):
    fig = weekly_volume_chart(workout_df)
    assert fig is not None
    assert len(fig.axes) == 1


def test_weekly_volume_chart_insufficient_data():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-10-05"]),
            "sets": [3],
            "reps": [5],
            "weight_kg": [100.0],
        }
    )
    fig = weekly_volume_chart(df)
    assert fig is not None


def test_sleep_chart_returns_figure(recovery_df):
    fig = sleep_chart(recovery_df)
    assert fig is not None
    assert len(fig.axes) == 1


def test_sleep_chart_insufficient_data():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-10-05"]),
            "sleep_hours": [7.5],
        }
    )
    fig = sleep_chart(df)
    assert fig is not None


def test_muscle_workload_chart_returns_figure(workout_df):
    df = workout_df.copy()
    df["volume_kg"] = df["sets"] * df["reps"] * df["weight_kg"]
    fig = muscle_workload_chart(df)
    assert fig is not None
    assert len(fig.axes) == 1


def test_muscle_workload_chart_insufficient_data():
    df = pd.DataFrame(
        {
            "muscle_group": ["Chest"],
            "volume_kg": [100.0],
        }
    )
    fig = muscle_workload_chart(df)
    # One muscle group should still render (not insufficient)
    assert fig is not None


def test_body_weight_chart_returns_figure(recovery_df):
    fig = body_weight_chart(recovery_df)
    assert fig is not None
    assert len(fig.axes) == 1


def test_body_weight_chart_insufficient_data():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-10-05"]),
            "body_weight_kg": [78.0],
        }
    )
    fig = body_weight_chart(df)
    assert fig is not None


def test_rpe_chart_returns_figure(workout_df):
    fig = rpe_chart(workout_df)
    assert fig is not None
    assert len(fig.axes) == 1


def test_rpe_chart_insufficient_data():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-10-05"]),
            "rpe": [7.0],
        }
    )
    fig = rpe_chart(df)
    assert fig is not None


def test_export_figure_to_png(tmp_path):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 2, 3])
    filepath = tmp_path / "test_chart.png"
    export_figure_to_png(fig, str(filepath))
    assert filepath.exists()
    plt.close(fig)


# ------------------------------------------------------------------ report generator tests


def test_daily_summary_report(workout_df, recovery_df):
    report = daily_summary_report(workout_df, recovery_df, target_date="2026-10-05")
    assert report["date"] == "2026-10-05"
    assert "workout" in report
    assert "recovery" in report
    assert "interpretation" in report
    assert report["workout"]["n_sets"] == 3
    assert report["workout"]["n_exercises"] == 2
    assert isinstance(report["interpretation"], str)


def test_daily_summary_report_no_date(workout_df, recovery_df):
    report = daily_summary_report(workout_df, recovery_df)
    assert "date" in report
    assert "interpretation" in report


def test_weekly_report(workout_df, recovery_df):
    report = weekly_report(workout_df, recovery_df, week_start="2026-10-05")
    assert report["week"] == "2026-10-05"
    assert "workout" in report
    assert "recovery" in report
    assert "interpretation" in report


def test_monthly_report(workout_df, recovery_df):
    report = monthly_report(workout_df, recovery_df, year=2026, month=10)
    assert report["month"] == "2026-10"
    assert "workout" in report
    assert "recovery" in report
    assert "interpretation" in report


def test_detection_alerts_report():
    results = [
        {
            "detected": True,
            "severity": "warning",
            "reason": "plateau_detected",
            "explanation": "Strength plateau detected for Bench Press.",
            "guidance": "Consider varying rep ranges.",
            "observed": {"total_improvement_pct": 1.0},
        },
        {
            "detected": True,
            "severity": "alert",
            "reason": "significant_spike",
            "explanation": "Workload spike detected.",
            "guidance": "Reduce volume.",
            "observed": {"volume_change_pct": 25.0},
        },
        {
            "detected": False,
            "severity": "info",
            "reason": "no_fatigue",
            "explanation": "No fatigue detected.",
            "guidance": "Continue monitoring.",
            "observed": {},
        },
    ]
    report = detection_alerts_report(results)
    assert report["total_alerts"] == 2
    assert report["severity_counts"]["warning"] == 1
    assert report["severity_counts"]["alert"] == 1
    assert len(report["alerts"]) == 2
    assert isinstance(report["interpretation"], str)


def test_detection_alerts_report_empty():
    report = detection_alerts_report([])
    assert report["total_alerts"] == 0
    assert "No detection alerts" in report["interpretation"]
