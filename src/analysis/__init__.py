"""Exploratory data analysis package (Phases 5 and 7)."""

from src.analysis.eda import (
    EDAResult,
    average_rpe,
    body_weight_changes,
    exercise_frequency,
    muscle_group_workload,
    recovery_vs_performance,
    sleep_patterns,
    summary_report,
    training_volume_distribution,
    workout_frequency,
)
from src.analysis.recovery import (
    recovery_daily_averages,
    recovery_period_changes,
    recovery_performance_correlation,
    recovery_rolling_averages,
    recovery_summary_report,
    recovery_weekly_averages,
    sleep_consistency,
)

__all__ = [
    "EDAResult",
    "average_rpe",
    "body_weight_changes",
    "exercise_frequency",
    "muscle_group_workload",
    "recovery_daily_averages",
    "recovery_period_changes",
    "recovery_performance_correlation",
    "recovery_rolling_averages",
    "recovery_summary_report",
    "recovery_vs_performance",
    "recovery_weekly_averages",
    "sleep_consistency",
    "sleep_patterns",
    "summary_report",
    "training_volume_distribution",
    "workout_frequency",
]
