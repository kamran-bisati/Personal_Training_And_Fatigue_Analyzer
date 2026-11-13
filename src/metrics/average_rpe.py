"""Average RPE calculations.

Phase 6 deliverable. Pure functions — no side effects, no validation
dependency. Callers validate inputs before they reach this module.
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd


def average_rpe(rpe_values: Iterable[float]) -> float:
    """Calculate the mean RPE across a collection of values.

    Args:
        rpe_values: Iterable of RPE values (each should be 1-10, but no
            range enforcement is performed here — validation is the caller's
            responsibility).

    Returns:
        Mean RPE as a float. Returns 0.0 for an empty iterable.

    Raises:
        TypeError: If any element is not numeric.
        ValueError: If any element is negative.
    """
    values = [float(v) for v in rpe_values]
    for v in values:
        if v < 0:
            raise ValueError(f"RPE values must be non-negative, got {v}")
    if not values:
        return 0.0
    return sum(values) / len(values)


def bulk_average_rpe(
    df: pd.DataFrame,
    rpe_col: str = "rpe",
    group_col: str | None = None,
    output_col: str = "avg_rpe",
) -> pd.DataFrame:
    """Calculate average RPE from a DataFrame.

    Args:
        df: DataFrame containing set records.
        rpe_col: Column name for RPE values.
        group_col: Optional column to group by (e.g. ``"week"`` or
            ``"exercise"``). If None, returns a single-row DataFrame with the
            overall average.
        output_col: Output column name for the average RPE.

    Returns:
        If ``group_col`` is None: a single-row DataFrame with columns
        ``[output_col, n_records]``. Otherwise: a DataFrame with columns
        ``[group_col, output_col, n_records]`` sorted by ``group_col``.

    Raises:
        ValueError: If ``rpe_col`` is missing from ``df``.
        TypeError: If ``rpe_col`` is non-numeric.
    """
    if rpe_col not in df.columns:
        raise ValueError(f"missing required column: '{rpe_col}'")
    if not pd.api.types.is_numeric_dtype(df[rpe_col]):
        raise TypeError(f"column '{rpe_col}' must be numeric, got {df[rpe_col].dtype}")

    working = df.dropna(subset=[rpe_col]).copy()
    if working.empty:
        if group_col is None:
            return pd.DataFrame({output_col: [0.0], "n_records": [0]})
        return pd.DataFrame(columns=[group_col, output_col, "n_records"])

    if group_col is None:
        return pd.DataFrame(
            {
                output_col: [working[rpe_col].mean()],
                "n_records": [len(working)],
            }
        )

    if group_col not in df.columns:
        raise ValueError(f"group column '{group_col}' not found in DataFrame")

    result = (
        working.groupby(group_col)[rpe_col]
        .agg(["mean", "size"])
        .round(2)
        .rename(columns={"mean": output_col, "size": "n_records"})
        .reset_index()
        .sort_values(group_col)
        .reset_index(drop=True)
    )
    return result
