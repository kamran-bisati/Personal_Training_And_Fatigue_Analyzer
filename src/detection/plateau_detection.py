"""Strength plateau detection.

Phase 8 deliverable. Pure functions — no side effects, no validation
dependency. Callers validate inputs before they reach this module.

Detects when estimated 1RM for an exercise stops improving over a
configurable period (default 4-6 weeks) with sufficient observations
(default >= 4 sessions).

IMPORTANT: These are initial engineering rules, not scientifically
validated universal thresholds. Require sufficient historical data and
explain the conditions behind every detection.
"""

from __future__ import annotations

import pandas as pd

from src.metrics.estimated_1rm import bulk_estimated_1rm
from src.config.thresholds import DETECTION_THRESHOLDS, ThresholdConfig


def detect_plateau(
    workout_df: pd.DataFrame,
    exercise: str | None = None,
    thresholds: ThresholdConfig | None = None,
) -> dict:
    """Detect a possible strength plateau for an exercise.

    Args:
        workout_df: DataFrame with workout set records. Must contain
            ``date``, ``exercise``, ``sets``, ``reps``, ``weight_kg``.
        exercise: Exercise name to check. If None, checks all exercises
            individually and returns the first plateau found (or None).
        thresholds: Optional threshold config override.

    Returns:
        A detection result dict with keys:
        ``detected``, ``exercise``, ``conditions``, ``observed``,
        ``explanation``, ``guidance``, ``severity``.

        Returns ``{"detected": False, "exercise": ..., "reason": ...}``
        when there is insufficient data to evaluate.

    Raises:
        ValueError: If required columns are missing.
        TypeError: If required columns are non-numeric.
    """
    if thresholds is None:
        thresholds = DETECTION_THRESHOLDS

    required = ["date", "exercise", "sets", "reps", "weight_kg"]
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
    df = df.dropna(subset=["date", "exercise", "sets", "reps", "weight_kg"])
    if df.empty:
        return {
            "detected": False,
            "exercise": exercise or "all",
            "reason": "insufficient_data",
            "conditions": ["no valid workout records after cleaning"],
            "observed": {},
            "explanation": "No valid workout records available to evaluate a plateau.",
            "guidance": "Log more workout sessions before running plateau detection.",
            "severity": "info",
        }

    if exercise is not None:
        df = df[df["exercise"] == exercise].copy()
        if df.empty:
            return {
                "detected": False,
                "exercise": exercise,
                "reason": "no_data_for_exercise",
                "conditions": [f"no workout records for exercise '{exercise}'"],
                "observed": {},
                "explanation": f"No workout records found for exercise '{exercise}'.",
                "guidance": f"Log sessions for '{exercise}' before running plateau detection.",
                "severity": "info",
            }

    # Calculate e1RM per set row, then take the best (max) e1RM per session.
    df = bulk_estimated_1rm(df)
    df = df.dropna(subset=["e1rm_kg"])

    # Best e1RM per session (date + exercise).
    session_best = (
        df.groupby(["date", "exercise"])["e1rm_kg"]
        .max()
        .reset_index()
        .sort_values("date")
        .reset_index(drop=True)
    )

    n_sessions = len(session_best)
    if n_sessions < thresholds.plateau_min_sessions:
        return {
            "detected": False,
            "exercise": exercise or session_best["exercise"].iloc[0],
            "reason": "insufficient_sessions",
            "conditions": [
                f"sessions found: {n_sessions} "
                f"(minimum required: {thresholds.plateau_min_sessions})"
            ],
            "observed": {
                "n_sessions": n_sessions,
                "min_sessions_required": thresholds.plateau_min_sessions,
            },
            "explanation": (
                f"Only {n_sessions} session(s) found for this exercise. "
                f"At least {thresholds.plateau_min_sessions} are needed to "
                f"detect a plateau reliably."
            ),
            "guidance": (
                f"Log {thresholds.plateau_min_sessions - n_sessions} more "
                f"session(s) for this exercise before re-running plateau detection."
            ),
            "severity": "info",
        }

    # Check duration: sessions must span at least min_weeks.
    first_date = session_best["date"].iloc[0]
    last_date = session_best["date"].iloc[-1]
    weeks_span = (last_date - first_date).days / 7.0
    if weeks_span < thresholds.plateau_min_weeks:
        return {
            "detected": False,
            "exercise": exercise or session_best["exercise"].iloc[0],
            "reason": "insufficient_duration",
            "conditions": [
                f"weeks spanned: {weeks_span:.1f} "
                f"(minimum required: {thresholds.plateau_min_weeks})"
            ],
            "observed": {
                "n_sessions": n_sessions,
                "weeks_spanned": round(weeks_span, 1),
                "min_weeks_required": thresholds.plateau_min_weeks,
            },
            "explanation": (
                f"Sessions span {weeks_span:.1f} week(s), but at least "
                f"{thresholds.plateau_min_weeks} weeks are needed to "
                f"distinguish a plateau from normal short-term variation."
            ),
            "guidance": (
                f"Continue training and log sessions over at least "
                f"{thresholds.plateau_min_weeks} weeks before re-running "
                f"plateau detection."
            ),
            "severity": "info",
        }

    # Only consider sessions within the max_weeks window.
    cutoff_date = last_date - pd.Timedelta(weeks=thresholds.plateau_max_weeks)
    recent = session_best[session_best["date"] >= cutoff_date].copy()
    if len(recent) < thresholds.plateau_min_sessions:
        recent = session_best  # fall back to all sessions if window is too restrictive

    first_e1rm = recent["e1rm_kg"].iloc[0]
    last_e1rm = recent["e1rm_kg"].iloc[-1]
    total_improvement_pct = ((last_e1rm - first_e1rm) / first_e1rm) * 100.0
    avg_weekly_improvement_pct = total_improvement_pct / max(weeks_span, 0.1)

    conditions = [
        f"sessions analyzed: {len(recent)} (minimum: {thresholds.plateau_min_sessions})",
        f"period analyzed: {weeks_span:.1f} weeks "
        f"(target: {thresholds.plateau_min_weeks}-{thresholds.plateau_max_weeks} weeks)",
        f"first e1RM: {first_e1rm:.1f} kg -> last e1RM: {last_e1rm:.1f} kg",
        f"total improvement: {total_improvement_pct:.1f}% "
        f"(threshold: <{thresholds.plateau_improvement_threshold_pct}% = plateau)",
    ]

    detected = total_improvement_pct < thresholds.plateau_improvement_threshold_pct

    if detected:
        explanation = (
            f"Strength plateau detected for '{recent['exercise'].iloc[0]}': "
            f"estimated 1RM improved only {total_improvement_pct:.1f}% over "
            f"{weeks_span:.1f} weeks (from {first_e1rm:.1f} kg to "
            f"{last_e1rm:.1f} kg), which is below the "
            f"{thresholds.plateau_improvement_threshold_pct}% threshold."
        )
        guidance = (
            "Consider varying rep ranges, adjusting volume, or adding a "
            "deload week. Rule-based suggestion, not medical advice."
        )
        severity = "warning"
    else:
        explanation = (
            f"No plateau detected for '{recent['exercise'].iloc[0]}': "
            f"estimated 1RM improved {total_improvement_pct:.1f}% over "
            f"{weeks_span:.1f} weeks, which meets or exceeds the "
            f"{thresholds.plateau_improvement_threshold_pct}% threshold."
        )
        guidance = "Continue current programming and monitor progress."
        severity = "info"

    return {
        "detected": detected,
        "exercise": recent["exercise"].iloc[0],
        "reason": "plateau_detected" if detected else "no_plateau",
        "conditions": conditions,
        "observed": {
            "n_sessions": len(recent),
            "weeks_spanned": round(weeks_span, 1),
            "first_e1rm_kg": round(first_e1rm, 1),
            "last_e1rm_kg": round(last_e1rm, 1),
            "total_improvement_pct": round(total_improvement_pct, 1),
            "avg_weekly_improvement_pct": round(avg_weekly_improvement_pct, 1),
            "threshold_pct": thresholds.plateau_improvement_threshold_pct,
        },
        "explanation": explanation,
        "guidance": guidance,
        "severity": severity,
    }


def detect_plateau_all_exercises(
    workout_df: pd.DataFrame,
    thresholds: ThresholdConfig | None = None,
) -> list[dict]:
    """Run plateau detection for every exercise in the DataFrame.

    Args:
        workout_df: DataFrame with workout set records.
        thresholds: Optional threshold config override.

    Returns:
        List of detection result dicts, one per exercise with sufficient
        data. Exercises with insufficient data are included with
        ``detected=False`` and a ``reason`` explaining why.
    """
    if thresholds is None:
        thresholds = DETECTION_THRESHOLDS

    if "exercise" not in workout_df.columns:
        raise ValueError("missing required column: 'exercise'")

    exercises = workout_df["exercise"].dropna().unique().tolist()
    results: list[dict] = []
    for name in exercises:
        result = detect_plateau(workout_df, exercise=name, thresholds=thresholds)
        results.append(result)
    return results
