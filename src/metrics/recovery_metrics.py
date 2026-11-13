"""Recovery metrics calculations.

Phase 6 deliverable. Pure functions — no side effects, no validation
dependency. Callers validate inputs before they reach this module.

Covers sleep, soreness, energy and body-weight trends over time.
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd


def recovery_summary(
    sleep_hours: Iterable[float],
    soreness: Iterable[float],
    energy: Iterable[float],
    body_weight_kg: Iterable[float],
) -> dict[str, float]:
    """Calculate summary recovery metrics from four parallel collections.

    Args:
        sleep_hours: Sleep duration values (hours).
        soreness: Muscle soreness values (1-10 scale).
        energy: Energy level values (1-10 scale).
        body_weight_kg: Body weight values (kg).

    Returns:
        Dictionary with keys:
        ``avg_sleep_h``, ``avg_soreness``, ``avg_energy``,
        ``avg_body_weight_kg``, ``latest_body_weight_kg``,
        ``body_weight_change_kg``.

    Raises:
        ValueError: If the collections have different lengths.
        TypeError: If any element is not numeric.
    """
    sleep = [float(v) for v in sleep_hours]
    sore = [float(v) for v in soreness]
    ener = [float(v) for v in energy]
    weight = [float(v) for v in body_weight_kg]

    if not (len(sleep) == len(sore) == len(ener) == len(weight)):
        raise ValueError(
            "all input collections must have the same length"
        )

    for label, values in (
        ("sleep_hours", sleep),
        ("soreness", sore),
        ("energy", ener),
        ("body_weight_kg", weight),
    ):
        for v in values:
            if v < 0:
                raise ValueError(f"{label} values must be non-negative, got {v}")

    n = len(sleep)
    if n == 0:
        return {
            "avg_sleep_h": 0.0,
            "avg_soreness": 0.0,
            "avg_energy": 0.0,
            "avg_body_weight_kg": 0.0,
            "latest_body_weight_kg": 0.0,
            "body_weight_change_kg": 0.0,
        }

    return {
        "avg_sleep_h": round(sum(sleep) / n, 2),
        "avg_soreness": round(sum(sore) / n, 2),
        "avg_energy": round(sum(ener) / n, 2),
        "avg_body_weight_kg": round(sum(weight) / n, 2),
        "latest_body_weight_kg": round(weight[-1], 2),
        "body_weight_change_kg": round(weight[-1] - weight[0], 2),
    }


def bulk_recovery_summary(
    df: pd.DataFrame,
    date_col: str = "date",
    sleep_col: str = "sleep_hours",
    soreness_col: str = "soreness",
    energy_col: str = "energy",
    weight_col: str = "body_weight_kg",
    group_col: str | None = None,
) -> pd.DataFrame:
    """Calculate recovery summaries from a DataFrame.

    Args:
        df: DataFrame containing recovery log records.
        date_col: Column name for the log date.
        sleep_col: Column name for sleep hours.
        soreness_col: Column name for soreness.
        energy_col: Column name for energy.
        weight_col: Column name for body weight.
        group_col: Optional column to group by (e.g. ``"week"``). If None,
            returns a single-row summary for the whole DataFrame.

    Returns:
        DataFrame with one row per group (or one row overall) and columns
        for each average metric plus latest body weight and total change.

    Raises:
        ValueError: If any required column is missing.
        TypeError: If any metric column is non-numeric.
    """
    required = [sleep_col, soreness_col, energy_col, weight_col]
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

    working = df.dropna(subset=required).copy()
    if date_col in df.columns:
        working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
        working = working.dropna(subset=[date_col]).sort_values(date_col)

    if working.empty:
        cols = [
            group_col] if group_col else []
        cols += [
            "avg_sleep_h", "avg_soreness", "avg_energy",
            "avg_body_weight_kg", "latest_body_weight_kg",
            "body_weight_change_kg",
        ]
        return pd.DataFrame(columns=cols)

    def _summarize(group: pd.DataFrame) -> pd.Series:
        n = len(group)
        if n == 0:
            return pd.Series({
                "avg_sleep_h": 0.0,
                "avg_soreness": 0.0,
                "avg_energy": 0.0,
                "avg_body_weight_kg": 0.0,
                "latest_body_weight_kg": 0.0,
                "body_weight_change_kg": 0.0,
            })
        return pd.Series({
            "avg_sleep_h": round(group[sleep_col].mean(), 2),
            "avg_soreness": round(group[soreness_col].mean(), 2),
            "avg_energy": round(group[energy_col].mean(), 2),
            "avg_body_weight_kg": round(group[weight_col].mean(), 2),
            "latest_body_weight_kg": round(group[weight_col].iloc[-1], 2),
            "body_weight_change_kg": round(
                group[weight_col].iloc[-1] - group[weight_col].iloc[0], 2
            ),
        })

    if group_col is None:
        summary = _summarize(working).to_frame().T
        return summary.reset_index(drop=True)

    if group_col not in df.columns:
        raise ValueError(f"group column '{group_col}' not found in DataFrame")

    result = working.groupby(group_col).apply(_summarize, include_groups=False)
    result = result.reset_index()
    return result
