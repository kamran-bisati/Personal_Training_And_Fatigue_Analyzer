"""Tests for the Phase 2 cleaning pipeline."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from src.data.data_cleaning import (
    apply_missing_strategy,
    clean_recovery_logs,
    clean_workout_sets,
    convert_dates,
    drop_exact_duplicates,
    split_errors,
)
from src.data.validation import validate_workout_sets

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


def test_convert_dates_returns_datetime() -> None:
    df = pd.DataFrame([workout_row()])
    result = convert_dates(df)
    assert pd.api.types.is_datetime64_any_dtype(result["date"])
    assert df["date"].dtype == object  # original untouched


def test_convert_dates_turns_invalid_into_nat() -> None:
    df = pd.DataFrame([workout_row(date="not-a-date")])
    assert pd.isna(convert_dates(df).at[0, "date"])


def test_drop_exact_duplicates_keeps_first() -> None:
    row = workout_row()
    df = pd.DataFrame([row, dict(row)])
    result = drop_exact_duplicates(df)
    assert len(result) == 1


def test_duplicates_are_removed_and_logged() -> None:
    row = workout_row()
    df = pd.DataFrame([row, dict(row)])
    result = clean_workout_sets(df)
    assert len(result.data) == 1
    assert result.log.rows_in == 2
    assert result.log.rows_out == 1
    assert any("duplicate" in action for action in result.log.actions)


def test_invalid_rows_are_rejected_not_silently_deleted() -> None:
    df = pd.DataFrame(
        [
            workout_row(date=BASE_DATE),
            workout_row(date=BASE_DATE + timedelta(days=1), reps=-8),
        ]
    )
    result = clean_workout_sets(df)
    assert len(result.data) == 1
    assert len(result.rejected) == 1
    assert result.rejected.at[0, "reps"] == -8


def test_valid_rows_are_kept() -> None:
    df = pd.DataFrame([workout_row(), workout_row(date=BASE_DATE + timedelta(days=1))])
    result = clean_workout_sets(df)
    assert len(result.data) == 2
    assert result.rejected.empty


def test_missing_strategy_keep_rejects_required_missing() -> None:
    df = pd.DataFrame([workout_row(weight_kg=None)])
    result = clean_workout_sets(df, missing_strategy="keep")
    assert result.data.empty
    assert len(result.rejected) == 1


def test_missing_strategy_drop_removes_row() -> None:
    df = pd.DataFrame(
        [
            workout_row(weight_kg=None),
            workout_row(date=BASE_DATE + timedelta(days=1)),
        ]
    )
    result = clean_workout_sets(df, missing_strategy="drop")
    assert len(result.data) == 1
    assert result.rejected.empty


def test_missing_strategy_median_fills_numeric() -> None:
    df = pd.DataFrame(
        [
            workout_row(weight_kg=80.0),
            workout_row(date=BASE_DATE + timedelta(days=1), weight_kg=90.0),
            workout_row(date=BASE_DATE + timedelta(days=2), weight_kg=None),
        ]
    )
    result = clean_workout_sets(df, missing_strategy="median")
    assert len(result.data) == 3
    assert 85.0 in result.data["weight_kg"].tolist()
    assert not result.data["weight_kg"].isna().any()


def test_apply_missing_strategy_rejects_unknown_strategy() -> None:
    with pytest.raises(ValueError):
        apply_missing_strategy(pd.DataFrame([workout_row()]), ["weight_kg"], "average")


def test_recovery_keep_preserves_row_with_missing_metric() -> None:
    df = pd.DataFrame([recovery_row(sleep_hours=None)])
    result = clean_recovery_logs(df, missing_strategy="keep")
    assert len(result.data) == 1
    assert result.data["sleep_hours"].isna().all()
    assert result.rejected.empty


def test_recovery_drop_removes_missing_metric_row() -> None:
    df = pd.DataFrame(
        [
            recovery_row(sleep_hours=None),
            recovery_row(date=BASE_DATE + timedelta(days=1)),
        ]
    )
    result = clean_recovery_logs(df, missing_strategy="drop")
    assert len(result.data) == 1


def test_split_errors_ignores_warnings() -> None:
    df = pd.DataFrame([workout_row(weight_kg=0.0)])
    issues = validate_workout_sets(df)
    valid, rejected = split_errors(df, issues)
    assert len(valid) == 1
    assert rejected.empty


def test_log_summary_is_readable() -> None:
    df = pd.DataFrame([workout_row(), workout_row(reps=-1)])
    result = clean_workout_sets(df)
    summary = result.log.summary()
    assert "rows in: 2" in summary
    assert "rows out: 1" in summary
