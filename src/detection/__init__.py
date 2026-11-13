"""Pattern detection engine (Phase 8).

Four independent detection modules:

* plateau_detection  - strength plateau signals
* workload_detection - excessive workload / volume spike alerts
* fatigue_detection  - accumulated fatigue indicators
* deload_detection   - potential deload signals

Each module exposes pure functions that take DataFrames (and optional
threshold overrides) and return a detection result dict with:

* ``detected`` - bool, whether the signal was found
* ``conditions`` - list of condition descriptions that were evaluated
* ``observed`` - dict of measured values
* ``explanation`` - human-readable explanation of the finding
* ``guidance`` - suggested action (rule-based, not medical advice)

The deload module can consume outputs from the fatigue and workload modules.
"""

from src.detection.deload_detection import detect_deload
from src.detection.fatigue_detection import detect_fatigue
from src.detection.plateau_detection import detect_plateau
from src.detection.workload_detection import detect_workload

__all__ = [
    "detect_deload",
    "detect_fatigue",
    "detect_plateau",
    "detect_workload",
]
