"""Fatigue detection.

Phase 8 deliverable. Pure functions — no side effects, no validation
dependency. Callers validate inputs before they reach this module.

Combines multiple recovery and performance indicators rather than relying
on a single measurement:

* Average RPE >= 8.5
* Average sleep < 6 hours
* Average soreness >= 7/10
* Average energy <= 4/10
* Declining performance (e1RM trend)

Each qualifying indicator adds 1 point. A score of 3 or more indicates
elevated fatigue signals.

IMPORTANT: These are initial engineering rules, not scientifically
validated universal thresholds. Require sufficient historical data and
explain the conditions behind every detection.
"""

from __future__ import annotations

import pandas as pd

from src.metrics.estimated_1rm import bulk_estimated_1rm
from src.metrics.progression import bulk_strength_progression
from src.config.thresholds import DETECTION_THRESHOLDS, ThresholdConfig


def detect_fatigue(
    workout_df: pd.DataFrame,
    recovery_df: pd.DataFrame,
    thresholds: ThresholdConfig | None = None,
) -> dict:
    """Detect accumulated fatigue signals from combined indicators.

    Args:
        workout_df: DataFrame with workout set records. Must contain
            ``date``, ``sets``, ``reps``, ``weight_kg``, ``rpe``.
        recovery_df: DataFrame with recovery log records. Must contain
            ``date``, ``sleep_hours``, ``soreness``, ``energy``.
        thresholds: Optional threshold config override.

    Returns:
        A detection result dict with keys:
        ``detected``, ``conditions``, ``observed``, ``explanation``,
        ``guidance``, ``severity``, ``fatigue_score``, ``indicators``.

        Returns ``{"detected": False, "reason": ...}`` when there is
        insufficient data to evaluate.

    Raises:
        ValueError: If required columns are missing.
        TypeError: If required columns are non-numeric.
    """
    if thresholds is None:
        thresholds = DETECTION_THRESHOLDS

    # Validate workout columns.
    workout_required = ["date", "sets", "reps", "weight_kg", "rpe"]
    workout_missing = [c for c in workout_required if c not in workout_df.columns]
    if workout_missing:
        raise ValueError(
            f"workout_df missing required column(s): {', '.join(workout_missing)}"
        )
    for col in ["sets", "reps", "weight_kg", "rpe"]:
        if not pd.api.types.is_numeric_dtype(workout_df[col]):
            raise TypeError(
                f"workout column '{col}' must be numeric, got {workout_df[col].dtype}"
            )

    # Validate recovery columns.
    recovery_required = ["date", "sleep_hours", "soreness", "energy"]
    recovery_missing = [c for c in recovery_required if c not in recovery_df.columns]
    if recovery_missing:
        raise ValueError(
            f"recovery_df missing required column(s): {', '.join(recovery_missing)}"
        )
    for col in ["sleep_hours", "soreness", "energy"]:
        if not pd.api.types.is_numeric_dtype(recovery_df[col]):
            raise TypeError(
                f"recovery column '{col}' must be numeric, got {recovery_df[col].dtype}"
            )

    workout = workout_df.copy()
    workout["date"] = pd.to_datetime(workout["date"], errors="coerce")
    workout = workout.dropna(subset=["date", "sets", "reps", "weight_kg", "rpe"])

    recovery = recovery_df.copy()
    recovery["date"] = pd.to_datetime(recovery["date"], errors="coerce")
    recovery = recovery.dropna(subset=["date", "sleep_hours", "soreness", "energy"])

    if workout.empty or recovery.empty:
        return {
            "detected": False,
            "reason": "insufficient_data",
            "conditions": [
                f"workout records: {len(workout)}",
                f"recovery records: {len(recovery)}",
            ],
            "observed": {},
            "explanation": "Insufficient workout or recovery data to evaluate fatigue.",
            "guidance": "Log both workout and recovery data before running fatigue detection.",
            "severity": "info",
        }

    indicators: list[dict] = []
    score = 0

    # --- Indicator 1: Average RPE ---
    avg_rpe = float(workout["rpe"].mean())
    rpe_flag = avg_rpe >= thresholds.fatigue_rpe_threshold
    if rpe_flag:
        score += 1
    indicators.append({
        "name": "average_rpe",
        "threshold": f">= {thresholds.fatigue_rpe_threshold}",
        "observed": round(avg_rpe, 1),
        "flagged": rpe_flag,
    })

    # --- Indicator 2: Average sleep ---
    avg_sleep = float(recovery["sleep_hours"].mean())
    sleep_flag = avg_sleep < thresholds.fatigue_sleep_threshold
    if sleep_flag:
        score += 1
    indicators.append({
        "name": "average_sleep_h",
        "threshold": f"< {thresholds.fatigue_sleep_threshold}",
        "observed": round(avg_sleep, 1),
        "flagged": sleep_flag,
    })

    # --- Indicator 3: Average soreness ---
    avg_soreness = float(recovery["soreness"].mean())
    soreness_flag = avg_soreness >= thresholds.fatigue_soreness_threshold
    if soreness_flag:
        score += 1
    indicators.append({
        "name": "average_soreness",
        "threshold": f">= {thresholds.fatigue_soreness_threshold}",
        "observed": round(avg_soreness, 1),
        "flagged": soreness_flag,
    })

    # --- Indicator 4: Average energy ---
    avg_energy = float(recovery["energy"].mean())
    energy_flag = avg_energy <= thresholds.fatigue_energy_threshold
    if energy_flag:
        score += 1
    indicators.append({
        "name": "average_energy",
        "threshold": f"<= {thresholds.fatigue_energy_threshold}",
        "observed": round(avg_energy, 1),
        "flagged": energy_flag,
    })

    # --- Indicator 5: Declining performance ---
    # Use e1RM progression trend over recent sessions.
    workout_with_e1rm = bulk_estimated_1rm(workout)
    workout_with_e1rm = workout_with_e1rm.dropna(subset=["e1rm_kg"])
    performance_declining = False
    perf_explanation = "not enough session data to assess performance trend"

    if len(workout_with_e1rm) >= 2:
        workout_with_e1rm = workout_with_e1rm.sort_values("date")
        workout_with_e1rm["week"] = workout_with_e1rm["date"].dt.to_period("W").astype(str)
        weekly_best = (
            workout_with_e1rm.groupby("week")["e1rm_kg"]
            .max()
            .reset_index()
            .sort_values("week")
            .reset_index(drop=True)
        )
        if len(weekly_best) >= 2:
            first_e1rm = weekly_best["e1rm_kg"].iloc[0]
            last_e1rm = weekly_best["e1rm_kg"].iloc[-1]
            perf_change_pct = ((last_e1rm - first_e1rm) / first_e1rm) * 100.0
            # Performance is "declining" if e1RM is trending down overall.
            performance_declining = perf_change_pct < 0
            perf_explanation = (
                f"weekly best e1RM changed {perf_change_pct:.1f}% "
                f"({first_e1rm:.1f} kg -> {last_e1rm:.1f} kg)"
            )
    if performance_declining:
        score += 1
    indicators.append({
        "name": "declining_performance",
        "threshold": "e1RM trend down over recent weeks",
        "observed": perf_explanation,
        "flagged": performance_declining,
    })

    elevated = score >= thresholds.fatigue_elevated_score

    conditions = [
        f"fatigue score: {score} (elevated threshold: >= {thresholds.fatigue_elevated_score})",
    ]
    for ind in indicators:
        flag_str = "YES" if ind["flagged"] else "no"
        conditions.append(
            f"{ind['name']}: {ind['observed']} (threshold {ind['threshold']}) -> {flag_str}"
        )

    if elevated:
        explanation = (
            f"Elevated fatigue signals detected (score: {score}/5). "
            f"{sum(1 for i in indicators if i['flagged'])} indicator(s) met their "
            f"thresholds. This suggests accumulated fatigue may be present."
        )
        guidance = (
            "Consider reducing training volume or intensity, prioritizing "
            "sleep, and monitoring recovery. Rule-based suggestion, not "
            "medical advice."
        )
        severity = "warning"
    else:
        explanation = (
            f"No elevated fatigue signals detected (score: {score}/5). "
            f"{sum(1 for i in indicators if i['flagged'])} indicator(s) met their "
            f"thresholds, which is below the {thresholds.fatigue_elevated_score}-point "
            f"elevation threshold."
        )
        guidance = "Continue monitoring recovery indicators weekly."
        severity = "info"

    return {
        "detected": elevated,
        "reason": "elevated_fatigue" if elevated else "no_elevated_fatigue",
        "conditions": conditions,
        "observed": {
            "fatigue_score": score,
            "elevated_threshold": thresholds.fatigue_elevated_score,
            "indicators": indicators,
            "avg_rpe": round(avg_rpe, 1),
            "avg_sleep_h": round(avg_sleep, 1),
            "avg_soreness": round(avg_soreness, 1),
            "avg_energy": round(avg_energy, 1),
        },
        "explanation": explanation,
        "guidance": guidance,
        "severity": severity,
        "fatigue_score": score,
        "indicators": indicators,
    }
