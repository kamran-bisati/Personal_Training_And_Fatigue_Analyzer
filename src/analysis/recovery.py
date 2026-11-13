"""Recovery analysis engine.

Phase 7 deliverable. Pure functions — no side effects, no validation
dependency. Callers validate inputs before they reach this module.

Analyses sleep, soreness, energy and body-weight trends over time, with
daily/weekly averages, rolling averages, period-over-period changes and
correlations against training performance.

Designed to work with DataFrames from ``src.data.sample_dataset`` (recovery_logs)
as well as with DataFrames loaded from SQLite (same column names).
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd


# ------------------------------------------------------------------ averages


def recovery_daily_averages(
    df: pd.DataFrame,
    date_col: str = "date",
    sleep_col: str = "sleep_hours",
    soreness_col: str = "soreness",
    energy_col: str = "energy",
    weight_col: str = "body_weight_kg",
) -> pd.DataFrame:
    """Average recovery metrics per calendar day.

    Args:
        df: DataFrame containing recovery log records.
        date_col: Column name for the log date.
        sleep_col: Column name for sleep hours.
        soreness_col: Column name for soreness.
        energy_col: Column name for energy.
        weight_col: Column name for body weight.

    Returns:
        DataFrame sorted by date with one row per date and averaged metrics.

    Raises:
        ValueError: If any required column is missing.
        TypeError: If any metric column is non-numeric.
    """
    required = [date_col, sleep_col, soreness_col, energy_col, weight_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"missing required column(s): {', '.join(missing)}")

    for col in [sleep_col, soreness_col, energy_col, weight_col]:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise TypeError(
                f"column '{col}' must be numeric, got {df[col].dtype}"
            )

    working = df.copy()
    working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
    working = working.dropna(subset=[date_col])

    result = (
        working.groupby(date_col)
        .agg(
            avg_sleep_h=(sleep_col, "mean"),
            avg_soreness=(soreness_col, "mean"),
            avg_energy=(energy_col, "mean"),
            avg_body_weight_kg=(weight_col, "mean"),
            n_records=(date_col, "size"),
        )
        .round(2)
        .reset_index()
        .sort_values(date_col)
        .reset_index(drop=True)
    )
    return result


def recovery_weekly_averages(
    df: pd.DataFrame,
    date_col: str = "date",
    sleep_col: str = "sleep_hours",
    soreness_col: str = "soreness",
    energy_col: str = "energy",
    weight_col: str = "body_weight_kg",
) -> pd.DataFrame:
    """Average recovery metrics per week (ISO week)."""
    required = [date_col, sleep_col, soreness_col, energy_col, weight_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"missing required column(s): {', '.join(missing)}")

    for col in [sleep_col, soreness_col, energy_col, weight_col]:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise TypeError(
                f"column '{col}' must be numeric, got {df[col].dtype}"
            )

    working = df.copy()
    working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
    working = working.dropna(subset=[date_col]).copy()
    working["week"] = working[date_col].dt.to_period("W").astype(str)

    result = (
        working.groupby("week")
        .agg(
            avg_sleep_h=(sleep_col, "mean"),
            avg_soreness=(soreness_col, "mean"),
            avg_energy=(energy_col, "mean"),
            avg_body_weight_kg=(weight_col, "mean"),
            n_days=(date_col, "nunique"),
        )
        .round(2)
        .reset_index()
        .sort_values("week")
        .reset_index(drop=True)
    )
    return result


# ------------------------------------------------------------- rolling averages


def recovery_rolling_averages(
    df: pd.DataFrame,
    window: int = 7,
    date_col: str = "date",
    sleep_col: str = "sleep_hours",
    soreness_col: str = "soreness",
    energy_col: str = "energy",
    weight_col: str = "body_weight_kg",
) -> pd.DataFrame:
    """Rolling averages over a fixed window (default 7 days).

    Args:
        df: DataFrame containing recovery log records.
        window: Rolling window size in days.
        date_col: Column name for the log date.
        sleep_col: Column name for sleep hours.
        soreness_col: Column name for soreness.
        energy_col: Column name for energy.
        weight_col: Column name for body weight.

    Returns:
        DataFrame sorted by date with rolling-average columns prefixed
        with ``roll_``.

    Raises:
        ValueError: If any required column is missing or window < 1.
        TypeError: If any metric column is non-numeric.
    """
    if window < 1:
        raise ValueError(f"window must be >= 1, got {window}")

    required = [date_col, sleep_col, soreness_col, energy_col, weight_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"missing required column(s): {', '.join(missing)}")

    for col in [sleep_col, soreness_col, energy_col, weight_col]:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise TypeError(
                f"column '{col}' must be numeric, got {df[col].dtype}"
            )

    working = df.copy()
    working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
    working = working.dropna(subset=[date_col]).sort_values(date_col)

    result = working.set_index(date_col)
    result["roll_sleep_h"] = result[sleep_col].rolling(window).mean().round(2)
    result["roll_soreness"] = result[soreness_col].rolling(window).mean().round(2)
    result["roll_energy"] = result[energy_col].rolling(window).mean().round(2)
    result["roll_body_weight_kg"] = result[weight_col].rolling(window).mean().round(2)
    result = result.reset_index()
    return result


# ------------------------------------------------------------- period changes


def recovery_period_changes(
    df: pd.DataFrame,
    period: Literal["week", "month"] = "week",
    date_col: str = "date",
    sleep_col: str = "sleep_hours",
    soreness_col: str = "soreness",
    energy_col: str = "energy",
    weight_col: str = "body_weight_kg",
) -> pd.DataFrame:
    """Period-over-period changes in recovery indicators.

    Computes the difference between the current period's average and the
    previous period's average for each recovery metric.

    Args:
        df: DataFrame containing recovery log records.
        period: Grouping period, ``"week"`` or ``"month"``.
        date_col: Column name for the log date.
        sleep_col: Column name for sleep hours.
        soreness_col: Column name for soreness.
        energy_col: Column name for energy.
        weight_col: Column name for body weight.

    Returns:
        DataFrame with one row per period, including change columns
        (``_change`` suffix) versus the previous period. The first period
        has NaN changes.

    Raises:
        ValueError: If any required column is missing.
        TypeError: If any metric column is non-numeric.
    """
    required = [date_col, sleep_col, soreness_col, energy_col, weight_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"missing required column(s): {', '.join(missing)}")

    for col in [sleep_col, soreness_col, energy_col, weight_col]:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise TypeError(
                f"column '{col}' must be numeric, got {df[col].dtype}"
            )

    working = df.copy()
    working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
    working = working.dropna(subset=[date_col]).copy()

    if period == "week":
        working["period"] = working[date_col].dt.to_period("W").astype(str)
    else:
        working["period"] = working[date_col].dt.to_period("M").astype(str)

    averages = (
        working.groupby("period")
        .agg(
            avg_sleep_h=(sleep_col, "mean"),
            avg_soreness=(soreness_col, "mean"),
            avg_energy=(energy_col, "mean"),
            avg_body_weight_kg=(weight_col, "mean"),
        )
        .round(2)
        .sort_index()
    )

    averages["sleep_change"] = averages["avg_sleep_h"].diff().round(2)
    averages["soreness_change"] = averages["avg_soreness"].diff().round(2)
    averages["energy_change"] = averages["avg_energy"].diff().round(2)
    averages["body_weight_change"] = (
        averages["avg_body_weight_kg"].diff().round(2)
    )

    return averages.reset_index()


# ------------------------------------------------------------- sleep consistency


def sleep_consistency(
    df: pd.DataFrame,
    date_col: str = "date",
    sleep_col: str = "sleep_hours",
    group_by: Literal["week", "month"] = "week",
) -> pd.DataFrame:
    """Measure sleep consistency per period using standard deviation and range.

    Lower standard deviation means more consistent sleep.

    Args:
        df: DataFrame containing recovery log records.
        date_col: Column name for the log date.
        sleep_col: Column name for sleep hours.
        group_by: Grouping period, ``"week"`` or ``"month"``.

    Returns:
        DataFrame with columns ``[period, std_sleep_h, range_sleep_h, n_days]``.

    Raises:
        ValueError: If any required column is missing.
        TypeError: If ``sleep_col`` is non-numeric.
    """
    required = [date_col, sleep_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"missing required column(s): {', '.join(missing)}")
    if not pd.api.types.is_numeric_dtype(df[sleep_col]):
        raise TypeError(
            f"column '{sleep_col}' must be numeric, got {df[sleep_col].dtype}"
        )

    working = df.copy()
    working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
    working = working.dropna(subset=[date_col, sleep_col]).copy()

    if group_by == "week":
        working["period"] = working[date_col].dt.to_period("W").astype(str)
    else:
        working["period"] = working[date_col].dt.to_period("M").astype(str)

    result = (
        working.groupby("period")[sleep_col]
        .agg(std_sleep_h="std", range_sleep_h=lambda x: x.max() - x.min(), n_days="size")
        .round(2)
        .reset_index()
        .sort_values("period")
        .reset_index(drop=True)
    )
    return result


# ------------------------------------------------------- recovery vs performance


def recovery_performance_correlation(
    recovery_df: pd.DataFrame,
    workout_df: pd.DataFrame,
    recovery_col: str = "sleep_hours",
    performance_col: str = "rpe",
    date_col: str = "date",
    method: Literal["pearson", "spearman"] = "pearson",
) -> dict[str, float]:
    """Correlate a daily recovery metric with a daily performance metric.

    Aligns recovery and workout records by date and computes the correlation
    between them. Because multiple set rows can exist for one session date,
    workout values are first averaged per date.

    Args:
        recovery_df: DataFrame containing recovery log records.
        workout_df: DataFrame containing workout set records.
        recovery_col: Recovery column to correlate (e.g. ``"sleep_hours"``).
        performance_col: Performance column to correlate (e.g. ``"rpe"``,
            ``"e1rm_kg"``, or ``"volume_kg"``).
        date_col: Column name for the date in both DataFrames.
        method: Correlation method, ``"pearson"`` or ``"spearman"``.

    Returns:
        Dictionary with keys ``correlation``, ``n_overlapping_days``, and
        ``method``. Returns ``correlation = None`` when there are fewer than
        2 overlapping days.

    Raises:
        ValueError: If any required column is missing.
        TypeError: If any metric column is non-numeric.
    """
    required_recovery = [date_col, recovery_col]
    required_workout = [date_col, performance_col]
    missing_r = [c for c in required_recovery if c not in recovery_df.columns]
    missing_w = [c for c in required_workout if c not in workout_df.columns]
    if missing_r:
        raise ValueError(
            f"recovery_df missing required column(s): {', '.join(missing_r)}"
        )
    if missing_w:
        raise ValueError(
            f"workout_df missing required column(s): {', '.join(missing_w)}"
        )
    for col in [recovery_col]:
        if not pd.api.types.is_numeric_dtype(recovery_df[col]):
            raise TypeError(
                f"recovery column '{col}' must be numeric, got {recovery_df[col].dtype}"
            )
    for col in [performance_col]:
        if not pd.api.types.is_numeric_dtype(workout_df[col]):
            raise TypeError(
                f"workout column '{col}' must be numeric, got {workout_df[col].dtype}"
            )

    recovery = recovery_df[[date_col, recovery_col]].copy()
    recovery[date_col] = pd.to_datetime(recovery[date_col], errors="coerce")
    recovery = recovery.dropna(subset=[date_col, recovery_col])

    workout = workout_df[[date_col, performance_col]].copy()
    workout[date_col] = pd.to_datetime(workout[date_col], errors="coerce")
    workout = workout.dropna(subset=[date_col, performance_col])

    # Average multiple workout rows per date
    workout_daily = (
        workout.groupby(date_col)[performance_col]
        .mean()
        .reset_index(name=performance_col)
    )

    merged = recovery.merge(workout_daily, on=date_col, how="inner")
    merged = merged.dropna(subset=[recovery_col, performance_col])

    if len(merged) < 2:
        return {
            "correlation": None,
            "n_overlapping_days": len(merged),
            "method": method,
        }

    try:
        corr = merged[recovery_col].corr(merged[performance_col], method=method)
    except ImportError as exc:
        if method == "spearman":
            raise ImportError(
                "scipy is required for Spearman correlation. "
                "Install it with: pip install scipy"
            ) from exc
        raise

    return {
        "correlation": round(float(corr), 3) if pd.notna(corr) else None,
        "n_overlapping_days": int(len(merged)),
        "method": method,
    }


# ------------------------------------------------------------- summary report


def recovery_summary_report(
    recovery_df: pd.DataFrame,
    workout_df: pd.DataFrame | None = None,
) -> dict[str, object]:
    """Produce a compact dictionary of headline recovery findings.

    Args:
        recovery_df: DataFrame containing recovery log records.
        workout_df: Optional DataFrame containing workout set records. If
            provided, recovery-vs-performance correlations are included.

    Returns:
        Dictionary with weekly averages, sleep consistency, period changes,
        and (optionally) correlations between recovery and performance.
    """
    report: dict[str, object] = {}

    # Weekly averages
    report["weekly_averages"] = recovery_weekly_averages(recovery_df)

    # Sleep consistency
    report["sleep_consistency"] = sleep_consistency(recovery_df)

    # Period-over-period changes
    report["period_changes"] = recovery_period_changes(recovery_df, period="week")

    # Correlations with performance (if workout data provided)
    if workout_df is not None and not workout_df.empty:
        correlations: dict[str, dict[str, object]] = {}
        for recovery_col in ["sleep_hours", "soreness", "energy"]:
            for performance_col in ["rpe", "e1rm_kg", "volume_kg"]:
                if performance_col not in workout_df.columns:
                    continue
                key = f"{recovery_col}_vs_{performance_col}"
                correlations[key] = recovery_performance_correlation(
                    recovery_df, workout_df, recovery_col, performance_col
                )
        report["correlations"] = correlations

    return report
