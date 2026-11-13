"""Muscle-group workload calculations.

Phase 6 deliverable. Pure functions — no side effects, no validation
dependency. Callers validate inputs before they reach this module.

Maps exercises to muscle groups and distributes training volume across them.
"""

from __future__ import annotations

from typing import Iterable, Mapping

import pandas as pd


def muscle_workload(
    volume_kg: float, muscle_group: str
) -> tuple[str, float]:
    """Record a single volume contribution for a muscle group.

    Args:
        volume_kg: Training volume in kg (must be >= 0).
        muscle_group: Name of the muscle group.

    Returns:
        A tuple of ``(muscle_group, volume_kg)``.

    Raises:
        ValueError: If volume is negative.
        TypeError: If volume is not numeric.
    """
    if not isinstance(volume_kg, (int, float)) or isinstance(volume_kg, bool):
        raise TypeError(
            f"volume_kg must be numeric, got {type(volume_kg).__name__}"
        )
    if volume_kg < 0:
        raise ValueError(f"volume_kg must be non-negative, got {volume_kg}")

    return (str(muscle_group), float(volume_kg))


def aggregate_muscle_workload(
    contributions: Iterable[tuple[str, float]]
) -> dict[str, float]:
    """Aggregate multiple muscle-group volume contributions.

    Args:
        contributions: Iterable of ``(muscle_group, volume_kg)`` tuples.

    Returns:
        Dictionary mapping each muscle group to its total volume in kg.

    Raises:
        TypeError: If any element is not a 2-tuple or volume is not numeric.
        ValueError: If any volume is negative.
    """
    totals: dict[str, float] = {}
    for contribution in contributions:
        if not isinstance(contribution, tuple) or len(contribution) != 2:
            raise TypeError(
                "each contribution must be a (muscle_group, volume_kg) tuple"
            )
        muscle_group, volume = contribution
        if not isinstance(volume, (int, float)) or isinstance(volume, bool):
            raise TypeError(
                f"volume must be numeric, got {type(volume).__name__}"
            )
        if volume < 0:
            raise ValueError(f"volume must be non-negative, got {volume}")
        key = str(muscle_group)
        totals[key] = totals.get(key, 0.0) + float(volume)
    return totals


def bulk_muscle_workload(
    df: pd.DataFrame,
    volume_col: str = "volume_kg",
    muscle_col: str = "muscle_group",
    output_col: str = "total_volume_kg",
    include_share: bool = True,
) -> pd.DataFrame:
    """Aggregate training volume by muscle group from a DataFrame.

    Args:
        df: DataFrame containing volume and muscle-group columns (typically
            output of ``bulk_training_volume``).
        volume_col: Column name for per-set volume in kg.
        muscle_col: Column name for muscle group.
        output_col: Output column name for total volume per muscle group.
        include_share: If True, also adds a ``share_pct`` column showing each
            group's percentage of total volume.

    Returns:
        DataFrame with columns ``[muscle_col, output_col]`` (and
        ``share_pct`` if requested), sorted by volume descending.

    Raises:
        ValueError: If ``volume_col`` or ``muscle_col`` is missing.
        TypeError: If ``volume_col`` is non-numeric.
    """
    required = [volume_col, muscle_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"missing required column(s): {', '.join(missing)}"
        )
    if not pd.api.types.is_numeric_dtype(df[volume_col]):
        raise TypeError(
            f"column '{volume_col}' must be numeric, got {df[volume_col].dtype}"
        )

    working = df.dropna(subset=[volume_col, muscle_col]).copy()
    if working.empty:
        cols = [muscle_col, output_col]
        if include_share:
            cols.append("share_pct")
        return pd.DataFrame(columns=cols)

    grouped = (
        working.groupby(muscle_col)[volume_col]
        .sum()
        .reset_index(name=output_col)
        .sort_values(output_col, ascending=False)
        .reset_index(drop=True)
    )

    total = grouped[output_col].sum()
    if include_share and total > 0:
        grouped["share_pct"] = (grouped[output_col] / total * 100).round(1)
    elif include_share:
        grouped["share_pct"] = 0.0

    return grouped
