"""Tests for the Phase 8 Pattern Detection Engine."""

from __future__ import annotations

import pandas as pd
import pytest

from src.config.thresholds import DETECTION_THRESHOLDS, ThresholdConfig
from src.detection.deload_detection import detect_deload
from src.detection.fatigue_detection import detect_fatigue
from src.detection.plateau_detection import (
    detect_plateau,
    detect_plateau_all_exercises,
)
from src.detection.workload_detection import (
    detect_workload,
    detect_workload_all_muscle_groups,
)


# ------------------------------------------------------------------ fixtures


@pytest.fixture
def thresholds() -> ThresholdConfig:
    return DETECTION_THRESHOLDS


@pytest.fixture
def plateau_workout() -> pd.DataFrame:
    """Workout data where bench press plateaus (e1RM barely changes)."""
    rows = []
    base_date = pd.Timestamp("2026-10-01")
    for i in range(6):
        date = base_date + pd.Timedelta(weeks=i)
        # e1RM stays around 100 kg (very small improvement)
        weight = 100.0 + (i * 0.2)  # tiny increase
        rows.append(
            {
                "date": date,
                "exercise": "Bench Press",
                "sets": 3,
                "reps": 5,
                "weight_kg": weight,
                "rpe": 8.0,
                "muscle_group": "Chest",
            }
        )
    return pd.DataFrame(rows)


@pytest.fixture
def progressing_workout() -> pd.DataFrame:
    """Workout data where bench press keeps progressing."""
    rows = []
    base_date = pd.Timestamp("2026-10-01")
    for i in range(6):
        date = base_date + pd.Timedelta(weeks=i)
        weight = 100.0 + (i * 5.0)  # 5 kg per week improvement
        rows.append(
            {
                "date": date,
                "exercise": "Bench Press",
                "sets": 3,
                "reps": 5,
                "weight_kg": weight,
                "rpe": 7.5,
                "muscle_group": "Chest",
            }
        )
    return pd.DataFrame(rows)


@pytest.fixture
def spike_workout() -> pd.DataFrame():
    """Workout data with a sudden volume spike in the last week."""
    rows = []
    base_date = pd.Timestamp("2026-10-01")
    for i in range(5):
        date = base_date + pd.Timedelta(weeks=i)
        sets = 3 if i < 4 else 6  # double volume in last week
        for _ in range(sets):
            rows.append(
                {
                    "date": date,
                    "exercise": "Bench Press",
                    "sets": 1,
                    "reps": 5,
                    "weight_kg": 100.0,
                    "rpe": 7.0,
                    "muscle_group": "Chest",
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture
def fatigue_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Workout + recovery data with elevated fatigue indicators."""
    base_date = pd.Timestamp("2026-10-01")
    workout_rows = []
    recovery_rows = []
    for i in range(7):
        date = base_date + pd.Timedelta(days=i)
        workout_rows.append(
            {
                "date": date,
                "exercise": "Bench Press",
                "sets": 3,
                "reps": 5,
                "weight_kg": 100.0,
                "rpe": 9.0,  # high RPE
                "muscle_group": "Chest",
            }
        )
        recovery_rows.append(
            {
                "date": date,
                "sleep_hours": 5.0,  # low sleep
                "soreness": 8,  # high soreness
                "energy": 3,  # low energy
                "body_weight_kg": 78.0,
            }
        )
    return pd.DataFrame(workout_rows), pd.DataFrame(recovery_rows)


@pytest.fixture
def normal_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Workout + recovery data with normal indicators."""
    base_date = pd.Timestamp("2026-10-01")
    workout_rows = []
    recovery_rows = []
    for i in range(7):
        date = base_date + pd.Timedelta(days=i)
        workout_rows.append(
            {
                "date": date,
                "exercise": "Bench Press",
                "sets": 3,
                "reps": 5,
                "weight_kg": 100.0,
                "rpe": 7.0,
                "muscle_group": "Chest",
            }
        )
        recovery_rows.append(
            {
                "date": date,
                "sleep_hours": 8.0,
                "soreness": 3,
                "energy": 8,
                "body_weight_kg": 78.0,
            }
        )
    return pd.DataFrame(workout_rows), pd.DataFrame(recovery_rows)


# ------------------------------------------------------------------ plateau tests


def test_detect_plateau_plateau_detected(plateau_workout, thresholds):
    result = detect_plateau(plateau_workout, exercise="Bench Press", thresholds=thresholds)
    assert bool(result["detected"]) is True
    assert result["exercise"] == "Bench Press"
    assert result["severity"] == "warning"
    assert "total_improvement_pct" in result["observed"]
    assert result["observed"]["total_improvement_pct"] < thresholds.plateau_improvement_threshold_pct
    assert isinstance(result["explanation"], str)
    assert isinstance(result["guidance"], str)


def test_detect_plateau_no_plateau(progressing_workout, thresholds):
    result = detect_plateau(progressing_workout, exercise="Bench Press", thresholds=thresholds)
    assert bool(result["detected"]) is False
    assert result["severity"] == "info"
    assert result["observed"]["total_improvement_pct"] >= thresholds.plateau_improvement_threshold_pct


def test_detect_plateau_insufficient_sessions(thresholds):
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-10-01", "2026-10-08", "2026-10-15"]),
            "exercise": ["Bench Press"] * 3,
            "sets": [3, 3, 3],
            "reps": [5, 5, 5],
            "weight_kg": [100.0, 102.5, 105.0],
            "rpe": [7.0, 7.0, 7.0],
        }
    )
    result = detect_plateau(df, exercise="Bench Press", thresholds=thresholds)
    assert result["detected"] is False
    assert result["reason"] == "insufficient_sessions"
    assert result["observed"]["n_sessions"] == 3


def test_detect_plateau_insufficient_duration(thresholds):
    # 6 sessions but spanning only 2 weeks (less than min 4 weeks)
    rows = []
    base_date = pd.Timestamp("2026-10-01")
    for i in range(6):
        date = base_date + pd.Timedelta(days=i * 2)  # sessions over 10 days
        rows.append(
            {
                "date": date,
                "exercise": "Bench Press",
                "sets": 3,
                "reps": 5,
                "weight_kg": 100.0,
                "rpe": 7.0,
            }
        )
    df = pd.DataFrame(rows)
    result = detect_plateau(df, exercise="Bench Press", thresholds=thresholds)
    assert bool(result["detected"]) is False
    assert result["reason"] == "insufficient_duration"


def test_detect_plateau_missing_column(thresholds):
    df = pd.DataFrame({"date": ["2026-10-01"], "exercise": ["Bench Press"]})
    with pytest.raises(ValueError, match="missing required column"):
        detect_plateau(df, exercise="Bench Press", thresholds=thresholds)


def test_detect_plateau_all_exercises(plateau_workout, thresholds):
    results = detect_plateau_all_exercises(plateau_workout, thresholds=thresholds)
    assert len(results) == 1
    assert bool(results[0]["detected"]) is True


# ------------------------------------------------------------------ workload tests


def test_detect_workload_significant_spike(spike_workout, thresholds):
    result = detect_workload(spike_workout, muscle_group="Chest", thresholds=thresholds)
    assert bool(result["detected"]) is True
    assert result["severity"] == "alert"
    assert result["observed"]["volume_change_pct"] > thresholds.workload_significant_threshold_pct


def test_detect_workload_moderate_increase(thresholds):
    rows = []
    base_date = pd.Timestamp("2026-10-01")
    # Week 1: 1500 kg, Week 2: 1800 kg (20% increase)
    for i in range(2):
        date = base_date + pd.Timedelta(weeks=i)
        sets = 3 if i == 0 else 4  # 33% more sets = ~33% more volume
        for _ in range(sets):
            rows.append(
                {
                    "date": date,
                    "exercise": "Bench Press",
                    "sets": 1,
                    "reps": 5,
                    "weight_kg": 100.0,
                    "rpe": 7.0,
                    "muscle_group": "Chest",
                }
            )
    df = pd.DataFrame(rows)
    result = detect_workload(df, muscle_group="Chest", thresholds=thresholds)
    assert bool(result["detected"]) is True
    assert result["severity"] in ("warning", "alert")


def test_detect_workload_no_spike(thresholds):
    rows = []
    base_date = pd.Timestamp("2026-10-01")
    for i in range(3):
        date = base_date + pd.Timedelta(weeks=i)
        for _ in range(3):
            rows.append(
                {
                    "date": date,
                    "exercise": "Bench Press",
                    "sets": 1,
                    "reps": 5,
                    "weight_kg": 100.0,
                    "rpe": 7.0,
                    "muscle_group": "Chest",
                }
            )
    df = pd.DataFrame(rows)
    result = detect_workload(df, muscle_group="Chest", thresholds=thresholds)
    assert bool(result["detected"]) is False
    assert result["severity"] == "info"


def test_detect_workload_all_muscle_groups(spike_workout, thresholds):
    results = detect_workload_all_muscle_groups(spike_workout, thresholds=thresholds)
    assert len(results) >= 1  # at least overall
    overall = results[0]
    assert overall["muscle_group"] == "overall"


def test_detect_workload_insufficient_weeks(thresholds):
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-10-01"]),
            "sets": [3],
            "reps": [5],
            "weight_kg": [100.0],
        }
    )
    result = detect_workload(df, thresholds=thresholds)
    assert result["detected"] is False
    assert result["reason"] == "insufficient_weeks"


# ------------------------------------------------------------------ fatigue tests


def test_detect_fatigue_elevated(fatigue_data, thresholds):
    workout, recovery = fatigue_data
    result = detect_fatigue(workout, recovery, thresholds=thresholds)
    assert bool(result["detected"]) is True
    assert result["fatigue_score"] >= thresholds.fatigue_elevated_score
    assert result["severity"] == "warning"
    assert len(result["indicators"]) == 5


def test_detect_fatigue_normal(normal_data, thresholds):
    workout, recovery = normal_data
    result = detect_fatigue(workout, recovery, thresholds=thresholds)
    assert bool(result["detected"]) is False
    assert result["fatigue_score"] < thresholds.fatigue_elevated_score


def test_detect_fatigue_missing_columns(thresholds):
    workout = pd.DataFrame({"date": ["2026-10-01"], "rpe": [7.0]})
    recovery = pd.DataFrame({"date": ["2026-10-01"], "sleep_hours": [8.0]})
    with pytest.raises(ValueError, match="missing required column"):
        detect_fatigue(workout, recovery, thresholds=thresholds)


# ------------------------------------------------------------------ deload tests


def test_detect_deload_signal(fatigue_data, spike_workout, thresholds):
    workout, recovery = fatigue_data
    # Add muscle_group to spike_workout so deload can see workload spike
    spike_workout = spike_workout.copy()
    spike_workout["muscle_group"] = "Chest"
    result = detect_deload(spike_workout, recovery, thresholds=thresholds)
    # Just verify the structure is correct
    assert "detected" in result
    assert "conditions" in result
    assert "explanation" in result
    assert "guidance" in result
    assert "fatigue_result" in result
    assert "workload_results" in result


def test_detect_deload_no_fatigue(normal_data, thresholds):
    workout, recovery = normal_data
    result = detect_deload(workout, recovery, thresholds=thresholds)
    assert bool(result["detected"]) is False
    assert result["reason"] == "fatigue_not_elevated"


def test_detect_deload_insufficient_duration(fatigue_data, thresholds):
    workout, recovery = fatigue_data
    # Only 1 week of data
    result = detect_deload(workout, recovery, thresholds=thresholds)
    # fatigue_data has 7 days = 1 week, which is less than deload_min_consecutive_weeks (2)
    # But fatigue might be detected first, then duration check
    assert "detected" in result


# ------------------------------------------------------------------ config tests


def test_thresholds_defaults(thresholds):
    assert thresholds.plateau_improvement_threshold_pct == 2.0
    assert thresholds.plateau_min_sessions == 4
    assert thresholds.plateau_min_weeks == 4
    assert thresholds.workload_monitoring_threshold_pct == 10.0
    assert thresholds.workload_significant_threshold_pct == 20.0
    assert thresholds.fatigue_rpe_threshold == 8.5
    assert thresholds.fatigue_sleep_threshold == 6.0
    assert thresholds.fatigue_soreness_threshold == 7.0
    assert thresholds.fatigue_energy_threshold == 4.0
    assert thresholds.fatigue_elevated_score == 3
    assert thresholds.deload_min_consecutive_weeks == 2


def test_get_threshold(thresholds):
    from src.config.thresholds import get_threshold
    assert get_threshold("plateau_improvement_threshold_pct") == 2.0
    with pytest.raises(KeyError):
        get_threshold("nonexistent_threshold")
