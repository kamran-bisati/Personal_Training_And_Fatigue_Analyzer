"""Strength progression calculations.

Phase 6 deliverable. Pure functions — no side effects, no validation
dependency. Callers validate inputs before they reach this module.

Strength progression is measured as the percentage change in estimated 1RM:

    progression_pct = (current_e1rm - previous_e1rm) / previous_e1rm × 100
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd


def strength_progression(
    previous_e1rm_kg: float, current_e1rm_kg: float
) -> float:
    """Calculate the percentage change in estimated 1RM between two values.

    Args:
        previous_e1rm_kg: Earlier estimated 1RM in kg (must be > 0).
        current_e1rm_kg: Later estimated 1RM in kg (must be >= 0).

    Returns:
        Percentage change. Positive means improvement, negative means decline.

    Raises:
        ValueError: If previous_e1rm_kg is not positive, or current is
            negative.
        TypeError: If any argument is not numeric.
    """
    if not isinstance(previous_e1rm_kg, (int, float)) or isinstance(
        previous_e1rm_kg, bool
    ):
        raise TypeError(
            f"previous_e1rm_kg must be numeric, got {type(previous_e1rm_kg).__name__}"
        )
    if not isinstance(current_e1rm_kg, (int, float)) or isinstance(
        current_e1rm_kg, bool
    ):
        raise TypeError(
            f"current_e1rm_kg must be numeric, got {type(current_e1rm_kg).__name__}"
        )

    if previous_e1rm_kg <= 0:
        raise ValueError(
            f"previous_e1rm_kg must be positive, got {previous_e1rm_kg}"
        )
    if current_e1rm_kg < 0:
        raise ValueError(
            f"current_e1rm_kg must be non-negative, got {current_e1rm_kg}"
        )

    return (float(current_e1rm_kg) - float(previous_e1rm_kg)) / float(
        previous_e1rm_kg
    ) * 100.0


def bulk_strength_progression(
    df: pd.DataFrame,
    e1rm_col: str = "e1rm_kg",
    date_col: str = "date",
    exercise_col: str | None = None,
    output_col: str = "progression_pct",
) -> pd.DataFrame:
    """Calculate e1RM progression for rows sorted by date.

    For each row, computes the percentage change from the previous row's
    e1RM. Optionally groups by exercise so progression is calculated within
    each exercise's history.

    Args:
        df: DataFrame containing e1RM values (typically output of
            ``bulk_estimated_1rm``).
        e1rm_col: Column name for estimated 1RM.
        date_col: Column name for the session date (used for ordering).
        exercise_col: Optional column to group by (e.g. ``"exercise"``).
            If None, progression is calculated across the whole DataFrame.
        output_col: Output column name for the progression percentage.

    Returns:
        A copy of ``df`` with a new ``output_col`` column. The first row in
        each group has ``NaN`` (no previous value to compare).

    Raises:
        ValueError: If ``e1rm_col`` or ``date_col`` is missing, or if
            ``exercise_col`` is specified but missing.
        TypeError: If ``e1rm_col`` is non-numeric.
    """
    required = [e1rm_col, date_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"missing required column(s): {', '.join(missing)}"
        )
    if exercise_col is not None and exercise_col not in df.columns:
        raise ValueError(f"exercise column '{exercise_col}' not found in DataFrame")
    if not pd.api.types.is_numeric_dtype(df[e1rm_col]):
        raise TypeError(
            f"column '{e1rm_col}' must be numeric, got {df[e1rm_col].dtype}"
        )

    result = df.copy()
    result[date_col] = pd.to_datetime(result[date_col], errors="coerce")

    if exercise_col is None:
        result = result.sort_values(date_col)
        result[output_col] = result[e1rm_col].pct_change().mul(100).round(2)
    else:
        result = result.sort_values([exercise_col, date_col])
        result[output_col] = (
            result.groupby(exercise_col)[e1rm_col]
            .pct_change()
            .mul(100)
            .round(2)
        )

    return result.reset_index(drop=True)
