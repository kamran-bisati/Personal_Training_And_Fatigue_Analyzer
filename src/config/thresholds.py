"""Central detection thresholds.

Phase 8 deliverable. All detection thresholds live here so they can be
refined and eventually personalized per user.

IMPORTANT: These are initial engineering rules, not scientifically
validated universal thresholds. They require sufficient historical data,
account for missing records, and are designed to avoid false alerts from
isolated sessions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThresholdConfig:
    """All detection thresholds in one place."""

    # --- Plateau detection ---
    # Minimum number of comparable sessions required before a plateau can be flagged.
    plateau_min_sessions: int = 4
    # Minimum weeks of history required before a plateau can be flagged.
    plateau_min_weeks: int = 4
    # Maximum weeks of history to consider for plateau detection.
    plateau_max_weeks: int = 6
    # Strength improvement below this percent (per week, averaged) counts as a plateau.
    plateau_improvement_threshold_pct: float = 2.0

    # --- Workload detection ---
    # Weekly volume increase above this percent triggers a monitoring flag.
    workload_monitoring_threshold_pct: float = 10.0
    # Weekly volume increase above this percent triggers a significant spike warning.
    workload_significant_threshold_pct: float = 20.0
    # Minimum number of weeks required to compute a workload change.
    workload_min_weeks: int = 2

    # --- Fatigue detection ---
    # Average RPE at or above this value is a fatigue indicator.
    fatigue_rpe_threshold: float = 8.5
    # Average sleep below this value (hours) is a fatigue indicator.
    fatigue_sleep_threshold: float = 6.0
    # Average soreness at or above this value (1-10) is a fatigue indicator.
    fatigue_soreness_threshold: float = 7.0
    # Average energy at or below this value (1-10) is a fatigue indicator.
    fatigue_energy_threshold: float = 4.0
    # Fatigue score (number of qualifying indicators) at or above this value
    # indicates elevated fatigue signals.
    fatigue_elevated_score: int = 3

    # --- Deload detection ---
    # Minimum number of consecutive weeks with elevated fatigue required
    # before a deload signal can be flagged.
    deload_min_consecutive_weeks: int = 2


# Default thresholds instance.
DETECTION_THRESHOLDS = ThresholdConfig()


def get_threshold(name: str) -> object:
    """Look up a single threshold by name.

    Args:
        name: Threshold attribute name (e.g. ``"plateau_improvement_threshold_pct"``).

    Returns:
        The threshold value.

    Raises:
        KeyError: If the threshold name does not exist.
    """
    if not hasattr(DETECTION_THRESHOLDS, name):
        raise KeyError(f"unknown threshold: {name}")
    return getattr(DETECTION_THRESHOLDS, name)
