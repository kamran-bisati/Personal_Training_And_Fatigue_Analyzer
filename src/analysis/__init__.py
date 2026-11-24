"""Exploratory data analysis package (Phase 5).

Exports only the EDA module. The recovery analysis module
(src.analysis.recovery) is part of Stage 7 and is intentionally excluded
from this package to keep Stage 1–5 self-contained.
"""

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

__all__ = [
    "EDAResult",
    "average_rpe",
    "body_weight_changes",
    "exercise_frequency",
    "muscle_group_workload",
    "recovery_vs_performance",
    "sleep_patterns",
    "summary_report",
    "training_volume_distribution",
    "workout_frequency",
]
