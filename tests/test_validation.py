"""Tests for the Phase 2 validation module."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from src.data.validation import (
    has_errors,
    issues_to_frame,
    validate_recovery_logs,
    validate_workout_sets,
)

BASE_DATE = date(2026, 10, 5)


def workout_row(**overrides) -> dict:
    row = {
        "date": BASE_DATE,
        "exercise": "Bench Press",
        "muscle_group": "Chest",
        "equipment": "Barbell",
        "sets": 4,
        "reps": 5,
        "weight_kg": 80.0,
        "rpe": 8.0,
        "session_duration_min": 70,
    }
    row.update(overrides)
    return row


def workout_frame(*rows: dict) -> pd.DataFrame:
    return pd.DataFrame(list(rows) if rows else [workout_row()])


def recovery_row(**overrides) -> dict:
    row = {
        "date": BASE_DATE,
        "day_type": "training",
        "sleep_hours": 7.5,
        "body_weight_kg": 78.0,
        "soreness": 3,
        "energy": 8,
    }
    row.update(overrides)
    return row


def recovery_frame(*rows: dict) -> pd.DataFrame:
    return pd.DataFrame(list(rows) if rows else [recovery_row()])


def codes(issues) -> set[str]:
    return {issue.code for issue in issues}


def by_severity(issues, severity) -> list:
    return [issue for issue in issues if issue.severity == severity]


# ---------------------------------------------------------------- workouts


def test_valid_workout_has_no_issues() -> None:
    assert validate_workout_sets(workout_frame()) == []


def test_negative_reps_is_an_error() -> None:
    issues = validate_workout_sets(workout_frame(workout_row(reps=-8)))
    assert has_errors(issues)
    assert "range_invalid" in codes(issues)


def test_rpe_above_ten_is_an_error() -> None:
    issues = validate_workout_sets(workout_frame(workout_row(rpe=15.0)))
    assert "range_invalid" in codes(issues)


def test_rpe_not_multiple_of_half_is_a_warning() -> None:
    issues = validate_workout_sets(workout_frame(workout_row(rpe=7.25)))
    assert "rpe_step" in codes(issues)
    assert not has_errors(issues)


def test_missing_weight_is_an_error() -> None:
    issues = validate_workout_sets(workout_frame(workout_row(weight_kg=None)))
    assert "missing_value" in codes(issues)
    assert has_errors(issues)


def test_non_numeric_reps_is_an_error() -> None:
    issues = validate_workout_sets(workout_frame(workout_row(reps="eight")))
    assert "type_invalid" in codes(issues)
    assert has_errors(issues)


def test_future_date_is_an_error() -> None:
    issues = validate_workout_sets(
        workout_frame(workout_row(date=date.today() + timedelta(days=5)))
    )
    assert "date_future" in codes(issues)


def test_date_before_minimum_is_an_error() -> None:
    issues = validate_workout_sets(workout_frame(workout_row(date=date(2019, 1, 1))))
    assert "date_too_old" in codes(issues)


def test_unparseable_date_is_an_error() -> None:
    issues = validate_workout_sets(workout_frame(workout_row(date="not-a-date")))
    assert "date_invalid" in codes(issues)


def test_exact_duplicate_row_is_flagged() -> None:
    row = workout_row()
    issues = validate_workout_sets(workout_frame(row, dict(row)))
    assert "duplicate_row" in codes(issues)


def test_same_date_and_exercise_is_flagged() -> None:
    issues = validate_workout_sets(
        workout_frame(workout_row(rpe=7.5), workout_row(rpe=9.0))
    )
    assert "duplicate_session_exercise" in codes(issues)


def test_barbell_with_zero_weight_is_a_warning() -> None:
    issues = validate_workout_sets(workout_frame(workout_row(weight_kg=0.0)))
    assert "zero_weight_barbell" in codes(issues)
    assert not has_errors(issues)


def test_implausible_sets_times_reps_is_a_warning() -> None:
    issues = validate_workout_sets(workout_frame(workout_row(sets=20, reps=15)))
    assert "implausible_volume" in codes(issues)


def test_volume_outlier_is_a_warning() -> None:
    rows = [
        workout_row(date=BASE_DATE + timedelta(days=offset), weight_kg=weight)
        for offset, weight in enumerate([20.0, 21.0, 22.0, 23.0, 400.0])
    ]
    issues = validate_workout_sets(workout_frame(*rows))
    outliers = [issue for issue in issues if issue.code == "outlier"]
    assert len(outliers) == 1
    assert outliers[0].row == 4
    assert outliers[0].severity == "warning"


def test_missing_required_column_is_reported() -> None:
    df = workout_frame().drop(columns=["reps"])
    issues = validate_workout_sets(df)
    missing_columns = [issue for issue in issues if issue.code == "missing_column"]
    assert len(missing_columns) == 1
    assert missing_columns[0].column == "reps"
    assert missing_columns[0].row is None


# ---------------------------------------------------------------- recovery


def test_valid_recovery_has_no_issues() -> None:
    assert validate_recovery_logs(recovery_frame()) == []


def test_energy_above_ten_is_an_error() -> None:
    issues = validate_recovery_logs(recovery_frame(recovery_row(energy=11)))
    assert "range_invalid" in codes(issues)
    assert has_errors(issues)


def test_missing_sleep_is_only_a_warning() -> None:
    issues = validate_recovery_logs(recovery_frame(recovery_row(sleep_hours=None)))
    assert "missing_value" in codes(issues)
    assert not has_errors(issues)


def test_duplicate_recovery_date_is_flagged() -> None:
    issues = validate_recovery_logs(
        recovery_frame(recovery_row(), recovery_row(sleep_hours=6.0))
    )
    assert "duplicate_date" in codes(issues)


def test_body_weight_jump_is_a_warning() -> None:
    issues = validate_recovery_logs(
        recovery_frame(
            recovery_row(date=BASE_DATE, body_weight_kg=78.0),
            recovery_row(date=BASE_DATE + timedelta(days=1), body_weight_kg=85.0),
        )
    )
    assert "weight_jump" in codes(issues)


def test_unusual_sleep_is_a_warning() -> None:
    issues = validate_recovery_logs(recovery_frame(recovery_row(sleep_hours=14.0)))
    assert "unusual_sleep" in codes(issues)
    assert "range_invalid" not in codes(issues)


def test_non_numeric_soreness_is_an_error() -> None:
    issues = validate_recovery_logs(recovery_frame(recovery_row(soreness="high")))
    assert "type_invalid" in codes(issues)


def test_recovery_future_date_is_an_error() -> None:
    issues = validate_recovery_logs(
        recovery_frame(recovery_row(date=date.today() + timedelta(days=1)))
    )
    assert "date_future" in codes(issues)


# ---------------------------------------------------------------- helpers


def test_issues_to_frame_keeps_columns_when_empty() -> None:
    frame = issues_to_frame([])
    assert list(frame.columns) == ["row", "column", "severity", "code", "message"]
    assert frame.empty


def test_issue_string_is_readable() -> None:
    issues = validate_workout_sets(workout_frame(workout_row(rpe=15.0)))
    assert "range_invalid" in str(issues[0])
