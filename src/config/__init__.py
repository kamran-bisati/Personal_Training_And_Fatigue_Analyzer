"""Configuration package for the Fitness Analytics System."""

from src.config.thresholds import (
    DETECTION_THRESHOLDS,
    ThresholdConfig,
    get_threshold,
)

__all__ = [
    "DETECTION_THRESHOLDS",
    "ThresholdConfig",
    "get_threshold",
]
