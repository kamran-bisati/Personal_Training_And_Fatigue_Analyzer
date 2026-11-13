"""Report generator.

Phase 9 deliverable. Pure functions that assemble analytical reports from
analysis and detection module outputs. Returns dictionaries and DataFrames
containing report data plus textual interpretations for accessibility.

Does not create charts directly - chart generation is handled by
``src.reporting.visualization``. Report functions can be combined with
chart figures for Streamlit display or PDF/HTML export.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from src.analysis.eda import summary_report as eda_summary_report
from src.analysis.recovery import recovery_summary_report as recovery_summary_report_fn


def daily_summary_report(
    workout_df: pd.DataFrame,
    recovery_df: pd.DataFrame,
    target_date: Optional[str] = None,
) -> dict:
    """Generate a daily summary report for a specific date.

    Args:
        workout_df: DataFrame with workout set records.
        recovery_df: DataFrame with recovery log records.
        target_date: Date string (YYYY-MM-DD). If None, uses the most
            recent date present in either DataFrame.

    Returns:
        Dictionary with workout summary, recovery summary, and
        textual interpretation for the day.
    """
    workout = workout_df.copy()
    recovery = recovery_df.copy()

    if "date" in workout.columns:
        workout["date"] = pd.to_datetime(workout["date"], errors="coerce")
    if "date" in recovery.columns:
        recovery["date"] = pd.to_datetime(recovery["date"], errors="coerce")

    # Determine target date
    if target_date is None:
        dates = []
        if "date" in workout.columns:
            dates.extend(workout["date"].dropna().tolist())
        if "date" in recovery.columns:
            dates.extend(recovery["date"].dropna().tolist())
        if not dates:
            return _empty_report("No data available")
        target_date = max(dates)
    else:
        target_date = pd.to_datetime(target_date)

    target_str = target_date.strftime("%Y-%m-%d")

    # Workout summary for the day
    if "date" in workout.columns:
        day_workout = workout[workout["date"] == target_date].copy()
    else:
        day_workout = pd.DataFrame()

    if not day_workout.empty:
        n_sets = int(len(day_workout))
        n_exercises = int(day_workout["exercise"].nunique()) if "exercise" in day_workout.columns else 0
        avg_rpe = float(day_workout["rpe"].mean()) if "rpe" in day_workout.columns else None

        if "volume_kg" in day_workout.columns:
            total_volume = float(day_workout["volume_kg"].sum())
        elif {"sets", "reps", "weight_kg"}.issubset(day_workout.columns):
            total_volume = float(
                (day_workout["sets"].astype(float)
                 * day_workout["reps"].astype(float)
                 * day_workout["weight_kg"].astype(float)).sum()
            )
        else:
            total_volume = 0.0
    else:
        total_volume = 0.0
        n_sets = 0
        n_exercises = 0
        avg_rpe = None

    # Recovery summary for the day
    if "date" in recovery.columns:
        day_recovery = recovery[recovery["date"] == target_date]
    else:
        day_recovery = pd.DataFrame()

    if not day_recovery.empty:
        sleep = float(day_recovery["sleep_hours"].iloc[0]) if "sleep_hours" in day_recovery.columns and pd.notna(day_recovery["sleep_hours"].iloc[0]) else None
        soreness = float(day_recovery["soreness"].iloc[0]) if "soreness" in day_recovery.columns and pd.notna(day_recovery["soreness"].iloc[0]) else None
        energy = float(day_recovery["energy"].iloc[0]) if "energy" in day_recovery.columns and pd.notna(day_recovery["energy"].iloc[0]) else None
        body_weight = float(day_recovery["body_weight_kg"].iloc[0]) if "body_weight_kg" in day_recovery.columns and pd.notna(day_recovery["body_weight_kg"].iloc[0]) else None
    else:
        sleep = soreness = energy = body_weight = None

    # Textual interpretation
    interpretation_parts = []
    if n_sets > 0:
        interpretation_parts.append(
            f"Completed {n_sets} set(s) across {n_exercises} exercise(s) "
            f"with total volume {total_volume:,.0f} kg."
        )
    else:
        interpretation_parts.append("No workout recorded for this day.")

    recovery_parts = []
    if sleep is not None:
        recovery_parts.append(f"Sleep: {sleep} h")
    if soreness is not None:
        recovery_parts.append(f"Soreness: {soreness}/10")
    if energy is not None:
        recovery_parts.append(f"Energy: {energy}/10")
    if body_weight is not None:
        recovery_parts.append(f"Body weight: {body_weight} kg")
    if recovery_parts:
        interpretation_parts.append("Recovery: " + ", ".join(recovery_parts) + ".")
    else:
        interpretation_parts.append("No recovery data recorded for this day.")

    return {
        "date": target_str,
        "workout": {
            "total_volume_kg": round(total_volume, 0),
            "n_sets": n_sets,
            "n_exercises": n_exercises,
            "avg_rpe": round(avg_rpe, 1) if avg_rpe is not None else None,
        },
        "recovery": {
            "sleep_hours": sleep,
            "soreness": soreness,
            "energy": energy,
            "body_weight_kg": body_weight,
        },
        "interpretation": " ".join(interpretation_parts),
    }


def weekly_report(
    workout_df: pd.DataFrame,
    recovery_df: pd.DataFrame,
    week_start: Optional[str] = None,
) -> dict:
    """Generate a weekly training and recovery report.

    Args:
        workout_df: DataFrame with workout set records.
        recovery_df: DataFrame with recovery log records.
        week_start: Week start date string (YYYY-MM-DD). If None, uses
            the most recent week in the data.

    Returns:
        Dictionary with weekly volume, frequency, RPE, recovery averages,
        and textual interpretation.
    """
    workout = workout_df.copy()
    recovery = recovery_df.copy()

    if "date" in workout.columns:
        workout["date"] = pd.to_datetime(workout["date"], errors="coerce")
    if "date" in recovery.columns:
        recovery["date"] = pd.to_datetime(recovery["date"], errors="coerce")

    # Determine target week
    if week_start is None:
        dates = []
        if "date" in workout.columns:
            dates.extend(workout["date"].dropna().tolist())
        if "date" in recovery.columns:
            dates.extend(recovery["date"].dropna().tolist())
        if not dates:
            return _empty_report("No data available")
        week_start = max(dates)
    else:
        week_start = pd.to_datetime(week_start)

    # Week boundaries (Monday to Sunday)
    week_start = week_start - pd.Timedelta(days=week_start.weekday())
    week_end = week_start + pd.Timedelta(days=6)
    week_str = week_start.strftime("%Y-%m-%d")

    # Filter to the week
    if "date" in workout.columns:
        week_workout = workout[
            (workout["date"] >= week_start) & (workout["date"] <= week_end)
        ].copy()
    else:
        week_workout = pd.DataFrame()

    if "date" in recovery.columns:
        week_recovery = recovery[
            (recovery["date"] >= week_start) & (recovery["date"] <= week_end)
        ].copy()
    else:
        week_recovery = pd.DataFrame()

    # Workout metrics
    if not week_workout.empty:
        n_sessions = int(week_workout["date"].nunique())
        n_exercises = int(week_workout["exercise"].nunique()) if "exercise" in week_workout.columns else 0
        avg_rpe = float(week_workout["rpe"].mean()) if "rpe" in week_workout.columns else None

        if "volume_kg" in week_workout.columns:
            total_volume = float(week_workout["volume_kg"].sum())
        elif {"sets", "reps", "weight_kg"}.issubset(week_workout.columns):
            total_volume = float(
                (week_workout["sets"].astype(float)
                 * week_workout["reps"].astype(float)
                 * week_workout["weight_kg"].astype(float)).sum()
            )
        else:
            total_volume = 0.0
    else:
        total_volume = 0.0
        n_sessions = 0
        n_exercises = 0
        avg_rpe = None

    # Recovery metrics
    recovery_metrics = {}
    if not week_recovery.empty:
        if "sleep_hours" in week_recovery.columns:
            recovery_metrics["avg_sleep_h"] = round(float(week_recovery["sleep_hours"].mean()), 2)
        if "soreness" in week_recovery.columns:
            recovery_metrics["avg_soreness"] = round(float(week_recovery["soreness"].mean()), 2)
        if "energy" in week_recovery.columns:
            recovery_metrics["avg_energy"] = round(float(week_recovery["energy"].mean()), 2)
        if "body_weight_kg" in week_recovery.columns:
            recovery_metrics["avg_body_weight_kg"] = round(float(week_recovery["body_weight_kg"].mean()), 2)
        recovery_metrics["n_days_logged"] = int(len(week_recovery))

    # Interpretation
    parts = [
        f"Week of {week_str}: {n_sessions} session(s), {n_exercises} exercise(s), "
        f"total volume {total_volume:,.0f} kg.",
    ]
    if avg_rpe is not None:
        parts.append(f"Average RPE: {avg_rpe:.1f}.")
    if recovery_metrics:
        rec_parts = []
        for k, v in recovery_metrics.items():
            if k == "n_days_logged":
                continue
            rec_parts.append(f"{k}: {v}")
        parts.append("Recovery: " + ", ".join(rec_parts) + ".")

    return {
        "week": week_str,
        "workout": {
            "total_volume_kg": round(total_volume, 0),
            "n_sessions": n_sessions,
            "n_exercises": n_exercises,
            "avg_rpe": round(avg_rpe, 1) if avg_rpe is not None else None,
        },
        "recovery": recovery_metrics,
        "interpretation": " ".join(parts),
    }


def monthly_report(
    workout_df: pd.DataFrame,
    recovery_df: pd.DataFrame,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> dict:
    """Generate a monthly training and recovery report.

    Args:
        workout_df: DataFrame with workout set records.
        recovery_df: DataFrame with recovery log records.
        year: Year for the report. If None, uses the most recent year
            in the data.
        month: Month for the report (1-12). If None, uses the most
            recent month in the data.

    Returns:
        Dictionary with monthly volume, sessions, recovery averages,
        and textual interpretation.
    """
    workout = workout_df.copy()
    recovery = recovery_df.copy()

    if "date" in workout.columns:
        workout["date"] = pd.to_datetime(workout["date"], errors="coerce")
    if "date" in recovery.columns:
        recovery["date"] = pd.to_datetime(recovery["date"], errors="coerce")

    # Determine target month
    dates = []
    if "date" in workout.columns:
        dates.extend(workout["date"].dropna().tolist())
    if "date" in recovery.columns:
        dates.extend(recovery["date"].dropna().tolist())

    if not dates:
        return _empty_report("No data available")

    if year is None:
        year = max(d.year for d in dates)
    if month is None:
        month = max(d.month for d in dates if d.year == year)

    month_str = f"{year:04d}-{month:02d}"

    # Filter to the month
    if "date" in workout.columns:
        month_workout = workout[
            (workout["date"].dt.year == year) & (workout["date"].dt.month == month)
        ].copy()
    else:
        month_workout = pd.DataFrame()

    if "date" in recovery.columns:
        month_recovery = recovery[
            (recovery["date"].dt.year == year) & (recovery["date"].dt.month == month)
        ].copy()
    else:
        month_recovery = pd.DataFrame()

    # Workout metrics
    if not month_workout.empty:
        n_sessions = int(month_workout["date"].nunique())
        n_exercises = int(month_workout["exercise"].nunique()) if "exercise" in month_workout.columns else 0
        avg_rpe = float(month_workout["rpe"].mean()) if "rpe" in month_workout.columns else None

        if "volume_kg" in month_workout.columns:
            total_volume = float(month_workout["volume_kg"].sum())
        elif {"sets", "reps", "weight_kg"}.issubset(month_workout.columns):
            total_volume = float(
                (month_workout["sets"].astype(float)
                 * month_workout["reps"].astype(float)
                 * month_workout["weight_kg"].astype(float)).sum()
            )
        else:
            total_volume = 0.0
    else:
        total_volume = 0.0
        n_sessions = 0
        n_exercises = 0
        avg_rpe = None

    # Recovery metrics
    recovery_metrics = {}
    if not month_recovery.empty:
        if "sleep_hours" in month_recovery.columns:
            recovery_metrics["avg_sleep_h"] = round(float(month_recovery["sleep_hours"].mean()), 2)
        if "soreness" in month_recovery.columns:
            recovery_metrics["avg_soreness"] = round(float(month_recovery["soreness"].mean()), 2)
        if "energy" in month_recovery.columns:
            recovery_metrics["avg_energy"] = round(float(month_recovery["energy"].mean()), 2)
        if "body_weight_kg" in month_recovery.columns:
            recovery_metrics["avg_body_weight_kg"] = round(float(month_recovery["body_weight_kg"].mean()), 2)
        recovery_metrics["n_days_logged"] = int(len(month_recovery))

    parts = [
        f"Month of {month_str}: {n_sessions} session(s), {n_exercises} exercise(s), "
        f"total volume {total_volume:,.0f} kg.",
    ]
    if avg_rpe is not None:
        parts.append(f"Average RPE: {avg_rpe:.1f}.")
    if recovery_metrics:
        rec_parts = []
        for k, v in recovery_metrics.items():
            if k == "n_days_logged":
                continue
            rec_parts.append(f"{k}: {v}")
        parts.append("Recovery: " + ", ".join(rec_parts) + ".")

    return {
        "month": month_str,
        "workout": {
            "total_volume_kg": round(total_volume, 0),
            "n_sessions": n_sessions,
            "n_exercises": n_exercises,
            "avg_rpe": round(avg_rpe, 1) if avg_rpe is not None else None,
        },
        "recovery": recovery_metrics,
        "interpretation": " ".join(parts),
    }


def detection_alerts_report(
    detection_results: list[dict],
) -> dict:
    """Assemble detection results into an alerts report.

    Args:
        detection_results: List of detection result dicts from the
            detection modules (plateau, workload, fatigue, deload).

    Returns:
        Dictionary with alert summary, counts by severity, and
        textual interpretations for each detection.
    """
    alerts = []
    for result in detection_results:
        if not isinstance(result, dict):
            continue
        if result.get("detected") and result.get("severity") in ("warning", "alert"):
            alerts.append(
                {
                    "reason": result.get("reason", "unknown"),
                    "explanation": result.get("explanation", ""),
                    "guidance": result.get("guidance", ""),
                    "severity": result.get("severity", "info"),
                    "observed": result.get("observed", {}),
                }
            )

    severity_counts = {"warning": 0, "alert": 0, "info": 0}
    for alert in alerts:
        sev = alert["severity"]
        if sev in severity_counts:
            severity_counts[sev] += 1

    total_alerts = len(alerts)

    if total_alerts == 0:
        interpretation = "No detection alerts. All metrics are within normal ranges."
    else:
        parts = [f"{total_alerts} detection alert(s) found:"]
        for alert in alerts:
            parts.append(f"• {alert['explanation']}")
        interpretation = " ".join(parts)

    return {
        "total_alerts": total_alerts,
        "severity_counts": severity_counts,
        "alerts": alerts,
        "interpretation": interpretation,
    }


# ------------------------------------------------------------------ helper


def _empty_report(message: str) -> dict:
    """Return a report structure indicating no data is available."""
    return {
        "error": message,
        "interpretation": message,
        "workout": {},
        "recovery": {},
    }
