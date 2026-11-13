"""Estimated 1-rep max calculations.

Phase 6 deliverable. Pure functions — no side effects, no validation
dependency. Callers validate inputs before they reach this module.

Epley formula:

    e1RM = Weight × (1 + Reps / 30)
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd


def estimated_1rm(weight_kg: float, reps: int) -> float:
    """Calculate estimated 1-rep max using the Epley formula.

    Args:
        weight_kg: Weight lifted in kilograms (must be >= 0).
        reps: Number of repetitions performed (must be > 0).

    Returns:
        Estimated 1RM in kg.

    Raises:
        ValueError: If weight is negative or reps is not positive.
        TypeError: If any argument is not numeric.
    """
    if not isinstance(weight_kg, (int, float)) or isinstance(weight_kg, bool):
        raise TypeError(f"weight_kg must be numeric, got {type(weight_kg).__name__}")
    if not isinstance(reps, (int, float)) or isinstance(reps, bool):
        raise TypeError(f"reps must be numeric, got {type(reps).__name__}")

    if weight_kg < 0:
        raise ValueError(f"weight_kg must be non-negative, got {weight_kg}")
    if reps <= 0:
        raise ValueError(f"reps must be positive, got {reps}")

    return float(weight_kg) * (1 + float(reps) / 30.0)


def bulk_estimated_1rm(
    df: pd.DataFrame,
    weight_col: str = "weight_kg",
    reps_col: str = "reps",
    e1rm_col: str = "e1rm_kg",
) -> pd.DataFrame:
    """Calculate estimated 1RM for every row in a DataFrame.

    Args:
        df: DataFrame containing set records.
        weight_col: Column name for weight in kg.
        reps_col: Column name for repetitions.
        e1rm_col: Output column name for estimated 1RM.

    Returns:
        A copy of ``df`` with a new ``e1rm_col`` column calculated via the
        Epley formula (Weight × (1 + Reps / 30)). Rows with missing values
        in any input column get ``NaN`` in the output.

    Raises:
        ValueError: If any required column is missing from ``df``.
        TypeError: If any required column is non-numeric.
    """
    required = [weight_col, reps_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"missing required column(s): {', '.join(missing)}"
        )

    for col in required:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise TypeError(
                f"column '{col}' must be numeric, got {df[col].dtype}"
            )

    result = df.copy()
    result[e1rm_col] = result[weight_col].astype(float) * (
        1 + result[reps_col].astype(float) / 30.0
    )
    return result
