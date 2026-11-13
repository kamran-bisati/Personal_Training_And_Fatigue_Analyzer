"""Reporting and visualization package (Phase 9).

Pure functions for generating Matplotlib Figure objects and assembling
analytical reports. Chart functions return Figure objects (not saved as
files by default) so Streamlit can display them with st.pyplot(fig).
Optional PNG export is available for reports and downloads.

Chart style: minimal and professional - white backgrounds, blue primary
color, subtle gridlines, clean typography, clear titles/axis labels/
legends/markers, accessible font sizes (12-14 pt), no color-only
communication, no 3D charts or visual clutter.
"""

from src.reporting.visualization import (
    strength_progression_chart,
    weekly_volume_chart,
    sleep_chart,
    muscle_workload_chart,
    body_weight_chart,
    rpe_chart,
    export_figure_to_png,
)
from src.reporting.report_generator import (
    daily_summary_report,
    weekly_report,
    monthly_report,
    detection_alerts_report,
)

__all__ = [
    "strength_progression_chart",
    "weekly_volume_chart",
    "sleep_chart",
    "muscle_workload_chart",
    "body_weight_chart",
    "rpe_chart",
    "export_figure_to_png",
    "daily_summary_report",
    "weekly_report",
    "monthly_report",
    "detection_alerts_report",
]
