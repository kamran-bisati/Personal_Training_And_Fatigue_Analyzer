"""Training volume calculations.

Phase 6 deliverable. Pure functions — no side effects, no validation
dependency. Callers validate inputs before they reach this module.

Volume formula:

    volume = sets × reps × weight
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd


def training_volume(sets: int, reps: int, weight_kg: float) -> float:
    """Calculate the volume of a single set.

    Args:
        sets: Number of sets (must be > 0).
        reps: Repetitions per set (must be > 0).
        weight_kg: Weight in kilograms (must be >= 0).

    Returns:
        Training volume in kg.

    Raises:
        ValueError: If sets or reps are not positive, or weight is negative.
        TypeError: If any argument is not numeric.
    """
    if not isinstance(sets, (int, float)) or isinstance(sets, bool):
        raise TypeError(f"sets must be numeric, got {type(sets).__name__}")
    if not isinstance(reps, (int, float)) or isinstance(reps, bool):
        raise TypeError(f"reps must be numeric, got {type(reps).__name__}")
    if not isinstance(weight_kg, (int, float)) or isinstance(weight_kg, bool):
        raise TypeError(f"weight_kg must be numeric, got {type(weight_kg).__name__}")

    if sets <= 0:
        raise ValueError(f"sets must be positive, got {sets}")
    if reps <= 0:
        raise ValueError(f"reps must be positive, got {reps}")
    if weight_kg < 0:
        raise ValueError(f"weight_kg must be non-negative, got {weight_kg}")

    return float(sets) * float(reps) * float(weight_kg)


def total_volume(volumes: Iterable[float]) -> float:
    """Sum individual set volumes into a total.

    Args:
        volumes: Iterable of per-set volumes (kg).

    Returns:
        Total volume in kg. Returns 0.0 for an empty iterable.

    Raises:
        TypeError: If any element is not numeric.
        ValueError: If any volume is negative.
    """
    total = 0.0
    for volume in volumes:
        if not isinstance(volume, (int, float)) or isinstance(volume, bool):
            raise TypeError(
                f"volume must be numeric, got {type(volume).__name__}"
            )
        if volume < 0:
            raise ValueError(f"volume must be non-negative, got {volume}")
        total += float(volume)
    return total


def bulk_training_volume(
    df: pd.DataFrame,
    sets_col: str = "sets",
    reps_col: str = "reps",
    weight_col: str = "weight_kg",
    volume_col: str = "volume_kg",
) -> pd.DataFrame:
    """Calculate volume for every row in a DataFrame.

    Args:
        df: DataFrame containing set records.
        sets_col: Column name for sets.
        reps_col: Column name for repetitions.
        weight_col: Column name for weight in kg.
        volume_col: Output column name for calculated volume.

    Returns:
        A copy of ``df`` with a new ``volume_col`` column (sets × reps × weight).
        Rows with missing values in any input column get ``NaN`` in the output.

    Raises:
        ValueError: If any required column is missing from ``df``.
        TypeError: If any required column is non-numeric.
    """
    required = [sets_col, reps_col, weight_col]
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
    result[volume_col] = (
        result[sets_col].astype(float)
        * result[reps_col].astype(float)
        * result[weight_col].astype(float)
    )
    return result
