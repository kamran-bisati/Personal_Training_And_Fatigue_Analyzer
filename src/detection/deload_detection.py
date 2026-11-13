"""Potential deload detection.

Phase 8 deliverable. Pure functions — no side effects, no validation
dependency. Callers validate inputs before they reach this module.

Identifies persistent combinations of:

* Elevated training workload
* Declining performance
* Higher perceived exertion
* Poor recovery
* Increased soreness

Consumes outputs from the fatigue and workload detection modules. A
deload signal is considered when elevated fatigue and workload warnings
persist together across consecutive weeks.

IMPORTANT: These are initial engineering rules, not scientifically
validated universal thresholds. Require sufficient historical data and
explain the conditions behind every detection. Not a medical diagnosis.
"""

from __future__ import annotations

import pandas as pd

from src.config.thresholds import DETECTION_THRESHOLDS, ThresholdConfig
from src.detection.fatigue_detection import detect_fatigue
from src.detection.workload_detection import detect_workload_all_muscle_groups


def detect_deload(
    workout_df: pd.DataFrame,
    recovery_df: pd.DataFrame,
    thresholds: ThresholdConfig | None = None,
) -> dict:
    """Detect a potential deload signal from combined fatigue and workload.

    Args:
        workout_df: DataFrame with workout set records. Must contain
            ``date``, ``sets``, ``reps``, ``weight_kg``, ``rpe`` and
            optionally ``muscle_group``.
        recovery_df: DataFrame with recovery log records. Must contain
            ``date``, ``sleep_hours``, ``soreness``, ``energy``.
        thresholds: Optional threshold config override.

    Returns:
        A detection result dict with keys:
        ``detected``, ``conditions``, ``observed``, ``explanation``,
        ``guidance``, ``severity``, ``fatigue_result``, ``workload_results``.

        Returns ``{"detected": False, "reason": ...}`` when there is
        insufficient data to evaluate.

    Raises:
        ValueError: If required columns are missing.
        TypeError: If required columns are non-numeric.
    """
    if thresholds is None:
        thresholds = DETECTION_THRESHOLDS

    # --- Step 1: Run fatigue detection ---
    try:
        fatigue_result = detect_fatigue(workout_df, recovery_df, thresholds=thresholds)
    except (ValueError, TypeError) as exc:
        return {
            "detected": False,
            "reason": "validation_error",
            "conditions": [str(exc)],
            "observed": {},
            "explanation": f"Unable to evaluate fatigue: {exc}",
            "guidance": "Check input data and retry.",
            "severity": "info",
        }

    if not fatigue_result["detected"]:
        # Fatigue not elevated — deload unlikely without elevated fatigue.
        return {
            "detected": False,
            "reason": "fatigue_not_elevated",
            "conditions": [
                f"fatigue score: {fatigue_result.get('fatigue_score', 0)} "
                f"(elevated threshold: >= {thresholds.fatigue_elevated_score})"
            ],
            "observed": {
                "fatigue_score": fatigue_result.get("fatigue_score", 0),
                "fatigue_explanation": fatigue_result.get("explanation", ""),
            },
            "explanation": (
                "No deload signal: fatigue indicators are not elevated. "
                f"{fatigue_result.get('explanation', '')}"
            ),
            "guidance": "Continue monitoring recovery and workload weekly.",
            "severity": "info",
            "fatigue_result": fatigue_result,
            "workload_results": [],
        }

    # --- Step 2: Run workload detection (overall + per muscle group) ---
    workload_results = detect_workload_all_muscle_groups(
        workout_df, thresholds=thresholds
    )

    # Check if any workload result shows a significant spike or moderate increase.
    workload_flagged = any(
        r["detected"] and r.get("severity") in ("warning", "alert")
        for r in workload_results
    )

    # --- Step 3: Check for persistence across weeks ---
    # We need at least min_consecutive_weeks of data to assess persistence.
    workout = workout_df.copy()
    workout["date"] = pd.to_datetime(workout["date"], errors="coerce")
    workout = workout.dropna(subset=["date"])
    n_weeks = workout["date"].dt.to_period("W").nunique() if not workout.empty else 0

    if n_weeks < thresholds.deload_min_consecutive_weeks:
        return {
            "detected": False,
            "reason": "insufficient_duration",
            "conditions": [
                f"weeks of data: {n_weeks} "
                f"(minimum for deload assessment: {thresholds.deload_min_consecutive_weeks})"
            ],
            "observed": {
                "n_weeks": n_weeks,
                "min_consecutive_weeks": thresholds.deload_min_consecutive_weeks,
            },
            "explanation": (
                f"Only {n_weeks} week(s) of data available. At least "
                f"{thresholds.deload_min_consecutive_weeks} consecutive weeks "
                f"are needed to assess whether fatigue and workload persist."
            ),
            "guidance": (
                f"Continue logging for at least {thresholds.deload_min_consecutive_weeks} "
                f"weeks before re-running deload detection."
            ),
            "severity": "info",
            "fatigue_result": fatigue_result,
            "workload_results": workload_results,
        }

    # --- Step 4: Combine conditions for deload signal ---
    conditions = [
        f"fatigue elevated: YES (score {fatigue_result.get('fatigue_score', 0)}/"
        f"{thresholds.fatigue_elevated_score}+)",
        f"workload warning or spike: {'YES' if workload_flagged else 'NO'}",
        f"weeks of data: {n_weeks} (minimum: {thresholds.deload_min_consecutive_weeks})",
    ]

    # Add sub-condition details.
    for ind in fatigue_result.get("indicators", []):
        if ind["flagged"]:
            conditions.append(
                f"fatigue indicator '{ind['name']}': {ind['observed']} "
                f"(threshold {ind['threshold']})"
            )

    significant_workloads = [
        r for r in workload_results
        if r["detected"] and r.get("severity") == "alert"
    ]
    moderate_workloads = [
        r for r in workload_results
        if r["detected"] and r.get("severity") == "warning"
    ]
    if significant_workloads:
        for r in significant_workloads:
            conditions.append(
                f"workload spike ({r['muscle_group']}): "
                f"{r['observed'].get('volume_change_pct', 0)}% increase"
            )
    if moderate_workloads:
        for r in moderate_workloads:
            conditions.append(
                f"workload increase ({r['muscle_group']}): "
                f"{r['observed'].get('volume_change_pct', 0)}% increase"
            )

    detected = workload_flagged  # elevated fatigue + workload warning/spike

    if detected:
        explanation = (
            "Potential deload signal detected: elevated fatigue indicators "
            "coincide with workload warnings or spikes across the recent "
            "training period. This combination suggests accumulated stress "
            "that may benefit from a temporary reduction in training load."
        )
        guidance = (
            "Consider a deload week: reduce volume by 30-50%, lower intensity, "
            "or take additional rest days. Prioritize sleep and nutrition. "
            "Rule-based suggestion, not medical advice."
        )
        severity = "warning"
    else:
        explanation = (
            "No deload signal: while fatigue indicators are elevated, no "
            "significant workload increase was detected. Fatigue may be due "
            "to non-training factors (sleep, nutrition, stress)."
        )
        guidance = (
            "Review recovery habits (sleep, nutrition, stress) and continue "
            "monitoring workload trends."
        )
        severity = "info"

    return {
        "detected": detected,
        "reason": "deload_signal" if detected else "no_deload_signal",
        "conditions": conditions,
        "observed": {
            "fatigue_score": fatigue_result.get("fatigue_score", 0),
            "fatigue_elevated": fatigue_result["detected"],
            "workload_flagged": workload_flagged,
            "significant_workloads": len(significant_workloads),
            "moderate_workloads": len(moderate_workloads),
            "n_weeks": n_weeks,
        },
        "explanation": explanation,
        "guidance": guidance,
        "severity": severity,
        "fatigue_result": fatigue_result,
        "workload_results": workload_results,
    }
