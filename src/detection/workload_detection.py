"""Excessive workload detection.

Phase 8 deliverable. Pure functions — no side effects, no validation
dependency. Callers validate inputs before they reach this module.

Calculates weekly training volume, compares recent weeks with previous
weeks, and flags unusually large increases (10% = monitoring, >20% =
significant spike). Analyzes both overall workload and per-muscle-group
workload.

IMPORTANT: These are initial engineering rules, not scientifically
validated universal thresholds. Require sufficient historical data and
explain the conditions behind every detection.
"""

from __future__ import annotations

import pandas as pd

from src.metrics.training_volume import bulk_training_volume
from src.config.thresholds import DETECTION_THRESHOLDS, ThresholdConfig


def detect_workload(
    workout_df: pd.DataFrame,
    muscle_group: str | None = None,
    thresholds: ThresholdConfig | None = None,
) -> dict:
    """Detect excessive workload spikes for overall or per-muscle-group volume.

    Args:
        workout_df: DataFrame with workout set records. Must contain
            ``date``, ``sets``, ``reps``, ``weight_kg`` and optionally
            ``muscle_group``.
        muscle_group: If set, only analyzes this muscle group. If None,
            analyzes overall workload across all exercises.
        thresholds: Optional threshold config override.

    Returns:
        A detection result dict with keys:
        ``detected``, ``muscle_group``, ``conditions``, ``observed``,
        ``explanation``, ``guidance``, ``severity``.

        Returns ``{"detected": False, "reason": ...}`` when there is
        insufficient data to evaluate.

    Raises:
        ValueError: If required columns are missing.
        TypeError: If required columns are non-numeric.
    """
    if thresholds is None:
        thresholds = DETECTION_THRESHOLDS

    required = ["date", "sets", "reps", "weight_kg"]
    missing = [c for c in required if c not in workout_df.columns]
    if missing:
        raise ValueError(f"missing required column(s): {', '.join(missing)}")
    for col in ["sets", "reps", "weight_kg"]:
        if not pd.api.types.is_numeric_dtype(workout_df[col]):
            raise TypeError(
                f"column '{col}' must be numeric, got {workout_df[col].dtype}"
            )

    df = workout_df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "sets", "reps", "weight_kg"])
    if df.empty:
        return {
            "detected": False,
            "muscle_group": muscle_group or "overall",
            "reason": "insufficient_data",
            "conditions": ["no valid workout records after cleaning"],
            "observed": {},
            "explanation": "No valid workout records available to evaluate workload.",
            "guidance": "Log more workout sessions before running workload detection.",
            "severity": "info",
        }

    if muscle_group is not None and "muscle_group" in df.columns:
        df = df[df["muscle_group"] == muscle_group].copy()
        if df.empty:
            return {
                "detected": False,
                "muscle_group": muscle_group,
                "reason": "no_data_for_muscle_group",
                "conditions": [f"no workout records for muscle group '{muscle_group}'"],
                "observed": {},
                "explanation": f"No workout records found for muscle group '{muscle_group}'.",
                "guidance": f"Log sessions for '{muscle_group}' before running workload detection.",
                "severity": "info",
            }

    # Calculate volume per set row.
    df = bulk_training_volume(df)
    df = df.dropna(subset=["volume_kg"])

    # Weekly volume.
    df["week"] = df["date"].dt.to_period("W").astype(str)
    weekly = (
        df.groupby("week")["volume_kg"]
        .sum()
        .reset_index(name="weekly_volume_kg")
        .sort_values("week")
        .reset_index(drop=True)
    )

    n_weeks = len(weekly)
    if n_weeks < thresholds.workload_min_weeks:
        return {
            "detected": False,
            "muscle_group": muscle_group or "overall",
            "reason": "insufficient_weeks",
            "conditions": [
                f"weeks found: {n_weeks} "
                f"(minimum required: {thresholds.workload_min_weeks})"
            ],
            "observed": {
                "n_weeks": n_weeks,
                "min_weeks_required": thresholds.workload_min_weeks,
            },
            "explanation": (
                f"Only {n_weeks} week(s) of data available. At least "
                f"{thresholds.workload_min_weeks} weeks are needed to "
                f"compute a workload change."
            ),
            "guidance": (
                f"Log sessions over at least {thresholds.workload_min_weeks} "
                f"weeks before re-running workload detection."
            ),
            "severity": "info",
        }

    # Compare the most recent week with the previous week.
    recent_week = weekly["weekly_volume_kg"].iloc[-1]
    previous_week = weekly["weekly_volume_kg"].iloc[-2]

    if previous_week <= 0:
        volume_change_pct = float("inf") if recent_week > 0 else 0.0
    else:
        volume_change_pct = ((recent_week - previous_week) / previous_week) * 100.0

    # Historical average (excluding the most recent week).
    historical_avg = weekly["weekly_volume_kg"].iloc[:-1].mean()

    conditions = [
        f"weeks analyzed: {n_weeks} (minimum: {thresholds.workload_min_weeks})",
        f"previous week volume: {previous_week:.0f} kg",
        f"recent week volume: {recent_week:.0f} kg",
        f"week-over-week change: {volume_change_pct:.1f}%",
        f"historical average (excl. recent): {historical_avg:.0f} kg",
        f"monitoring threshold: >{thresholds.workload_monitoring_threshold_pct}%",
        f"significant spike threshold: >{thresholds.workload_significant_threshold_pct}%",
    ]

    if volume_change_pct > thresholds.workload_significant_threshold_pct:
        detected = True
        severity = "alert"
        explanation = (
            f"Significant workload spike detected for "
            f"'{muscle_group or 'overall'}': weekly volume increased "
            f"{volume_change_pct:.1f}% (from {previous_week:.0f} kg to "
            f"{recent_week:.0f} kg), exceeding the "
            f"{thresholds.workload_significant_threshold_pct}% threshold."
        )
        guidance = (
            "Consider reducing volume or intensity next week, and prioritize "
            "recovery. Rule-based suggestion, not medical advice."
        )
    elif volume_change_pct > thresholds.workload_monitoring_threshold_pct:
        detected = True
        severity = "warning"
        explanation = (
            f"Workload increase detected for '{muscle_group or 'overall'}': "
            f"weekly volume increased {volume_change_pct:.1f}% (from "
            f"{previous_week:.0f} kg to {recent_week:.0f} kg), exceeding the "
            f"{thresholds.workload_monitoring_threshold_pct}% monitoring "
            f"threshold but below the {thresholds.workload_significant_threshold_pct}% "
            f"significant spike threshold."
        )
        guidance = (
            "Monitor closely. Consider maintaining current volume or a "
            "modest reduction if fatigue indicators are also present."
        )
    else:
        detected = False
        severity = "info"
        explanation = (
            f"No excessive workload detected for '{muscle_group or 'overall'}': "
            f"weekly volume changed {volume_change_pct:.1f}%, which is below "
            f"the {thresholds.workload_monitoring_threshold_pct}% monitoring threshold."
        )
        guidance = "Continue current programming and monitor weekly volume trends."

    return {
        "detected": detected,
        "muscle_group": muscle_group or "overall",
        "reason": (
            "significant_spike"
            if volume_change_pct > thresholds.workload_significant_threshold_pct
            else "moderate_increase"
            if volume_change_pct > thresholds.workload_monitoring_threshold_pct
            else "no_spike"
        ),
        "conditions": conditions,
        "observed": {
            "n_weeks": n_weeks,
            "previous_week_volume_kg": round(previous_week, 0),
            "recent_week_volume_kg": round(recent_week, 0),
            "volume_change_pct": round(volume_change_pct, 1),
            "historical_avg_volume_kg": round(historical_avg, 0),
            "monitoring_threshold_pct": thresholds.workload_monitoring_threshold_pct,
            "significant_threshold_pct": thresholds.workload_significant_threshold_pct,
        },
        "explanation": explanation,
        "guidance": guidance,
        "severity": severity,
    }


def detect_workload_all_muscle_groups(
    workout_df: pd.DataFrame,
    thresholds: ThresholdConfig | None = None,
) -> list[dict]:
    """Run workload detection for overall and each muscle group.

    Args:
        workout_df: DataFrame with workout set records.
        thresholds: Optional threshold config override.

    Returns:
        List of detection result dicts: one for overall workload plus one
        per muscle group that has data.
    """
    if thresholds is None:
        thresholds = DETECTION_THRESHOLDS

    results: list[dict] = []

    # Overall workload first.
    results.append(detect_workload(workout_df, muscle_group=None, thresholds=thresholds))

    # Per muscle group.
    if "muscle_group" in workout_df.columns:
        groups = workout_df["muscle_group"].dropna().unique().tolist()
        for group in groups:
            results.append(
                detect_workload(workout_df, muscle_group=group, thresholds=thresholds)
            )

    return results
