"""Fitness metrics calculation engine (Phase 6).

Pure functions for calculating training volume, estimated 1RM, average RPE,
strength progression, muscle-group workload and recovery metrics.

Each module provides:

* individual functions - raw numerical inputs, return a single result
* bulk functions - Pandas DataFrame inputs, return a DataFrame

The module is independent of validation. Callers are expected to validate
inputs before they reach the metrics engine. Individual functions include
basic safeguards and raise clear exceptions for invalid arguments.
"""

from src.metrics.training_volume import (
    training_volume,
    total_volume,
    bulk_training_volume,
)
from src.metrics.estimated_1rm import estimated_1rm, bulk_estimated_1rm
from src.metrics.average_rpe import average_rpe, bulk_average_rpe
from src.metrics.progression import (
    strength_progression,
    bulk_strength_progression,
)
from src.metrics.muscle_workload import (
    muscle_workload,
    aggregate_muscle_workload,
    bulk_muscle_workload,
)
from src.metrics.recovery_metrics import (
    recovery_summary,
    bulk_recovery_summary,
)

__all__ = [
    "training_volume",
    "total_volume",
    "bulk_training_volume",
    "estimated_1rm",
    "bulk_estimated_1rm",
    "average_rpe",
    "bulk_average_rpe",
    "strength_progression",
    "bulk_strength_progression",
    "muscle_workload",
    "aggregate_muscle_workload",
    "bulk_muscle_workload",
    "recovery_summary",
    "bulk_recovery_summary",
]
