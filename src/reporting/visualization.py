"""Chart visualization functions.

Phase 9 deliverable. All functions return Matplotlib Figure objects (not
saved as files by default) so Streamlit can display them with
``st.pyplot(fig)``. Optional PNG export is available via
``export_figure_to_png``.

Chart style: minimal and professional - white backgrounds, blue primary
color, subtle gridlines, clean typography, clear titles/axis labels/
legends/markers, accessible font sizes (12-14 pt), no color-only
communication, no 3D charts or visual clutter.

Accessibility standards:
* Readable font sizes (minimum 12-14 pt for chart labels)
* Sufficient contrast between text, chart elements and backgrounds
* Never communicate information through color alone (markers, line styles,
  labels or symbols as additional indicators)
* Descriptive chart titles, axis labels and measurement units
* No 3D charts, unnecessary visual effects, overcrowded labels or
  excessive data points
* Missing or insufficient data shown clearly instead of as zero
* Consistent typography, formatting and chart conventions throughout
"""

from __future__ import annotations

from typing import Optional

import matplotlib
matplotlib.use("Agg")  # non-interactive backend, safe for Streamlit
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

# ------------------------------------------------------------------ style constants

PRIMARY_COLOR = "#1f77b4"      # professional blue
SECONDARY_COLOR = "#ff7f0e"    # orange for secondary series
NEUTRAL_COLOR = "#7f7f7f"      # gray for neutral/missing data
GRID_COLOR = "#e0e0e0"         # subtle gridlines
TEXT_COLOR = "#333333"         # near-black for high contrast

TITLE_FONTSIZE = 14
LABEL_FONTSIZE = 12
TICK_FONTSIZE = 11
LEGEND_FONTSIZE = 11

MARKER_SIZE = 6
LINE_WIDTH = 2


def _apply_professional_style(ax: plt.Axes) -> None:
    """Apply consistent professional styling to an Axes object."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cccccc")
    ax.spines["bottom"].set_color("#cccccc")
    ax.tick_params(colors=TEXT_COLOR, labelsize=TICK_FONTSIZE)
    ax.grid(True, color=GRID_COLOR, linewidth=0.8, alpha=0.7)
    ax.set_axisbelow(True)


def _format_date_axis(ax: plt.Axes) -> None:
    """Format the x-axis for date data with readable tick labels."""
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")


def _handle_insufficient_data(
    ax: plt.Axes,
    message: str,
    title: str,
) -> plt.Figure:
    """Show a clear 'insufficient data' message instead of treating it as zero."""
    ax.text(
        0.5,
        0.5,
        message,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=LABEL_FONTSIZE,
        color=TEXT_COLOR,
        wrap=True,
    )
    ax.set_title(title, fontsize=TITLE_FONTSIZE, color=TEXT_COLOR, pad=15)
    _apply_professional_style(ax)
    return ax.figure


def _create_figure(figsize: tuple[float, float] = (10, 6)) -> plt.Figure:
    """Create a Figure with a white background."""
    fig = plt.figure(figsize=figsize, facecolor="white")
    return fig


# ------------------------------------------------------------------ strength progression


def strength_progression_chart(
    df: pd.DataFrame,
    date_col: str = "date",
    e1rm_col: str = "e1rm_kg",
    exercise_col: Optional[str] = None,
    exercise_name: Optional[str] = None,
    figsize: tuple[float, float] = (10, 6),
) -> plt.Figure:
    """Plot estimated 1RM over time for strength progression.

    Args:
        df: DataFrame with e1RM values (typically output of
            ``bulk_estimated_1rm`` plus ``bulk_strength_progression``).
        date_col: Column name for the session date.
        e1rm_col: Column name for estimated 1RM in kg.
        exercise_col: Optional column to filter by exercise name.
        exercise_name: If ``exercise_col`` is set, filter to this exercise.
        figsize: Figure size in inches.

    Returns:
        Matplotlib Figure object.
    """
    fig = _create_figure(figsize)
    ax = fig.add_subplot(111)

    working = df.copy()
    working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
    working = working.dropna(subset=[date_col, e1rm_col])

    if exercise_col is not None and exercise_name is not None:
        working = working[working[exercise_col] == exercise_name].copy()

    if working.empty or len(working) < 2:
        return _handle_insufficient_data(
            ax,
            "Insufficient data to plot strength progression.\n"
            "At least 2 sessions with valid e1RM values are required.",
            "Strength Progression - Estimated 1RM Over Time",
        )

    working = working.sort_values(date_col)

    ax.plot(
        working[date_col],
        working[e1rm_col],
        color=PRIMARY_COLOR,
        linewidth=LINE_WIDTH,
        marker="o",
        markersize=MARKER_SIZE,
        label="Estimated 1RM (kg)",
    )

    ax.set_title(
        f"Strength Progression - Estimated 1RM Over Time"
        + (f" ({exercise_name})" if exercise_name else ""),
        fontsize=TITLE_FONTSIZE,
        color=TEXT_COLOR,
        pad=15,
    )
    ax.set_ylabel("Estimated 1RM (kg)", fontsize=LABEL_FONTSIZE, color=TEXT_COLOR)
    ax.set_xlabel("Date", fontsize=LABEL_FONTSIZE, color=TEXT_COLOR)
    _format_date_axis(ax)
    _apply_professional_style(ax)
    ax.legend(fontsize=LEGEND_FONTSIZE, loc="best", frameon=False)

    fig.tight_layout()
    return fig


# ------------------------------------------------------------------ weekly training volume


def weekly_volume_chart(
    df: pd.DataFrame,
    date_col: str = "date",
    sets_col: str = "sets",
    reps_col: str = "reps",
    weight_col: str = "weight_kg",
    figsize: tuple[float, float] = (10, 6),
) -> plt.Figure:
    """Plot total weekly training volume as a bar chart.

    Args:
        df: DataFrame with workout set records.
        date_col: Column name for the session date.
        sets_col: Column name for sets.
        reps_col: Column name for repetitions.
        weight_col: Column name for weight in kg.
        figsize: Figure size in inches.

    Returns:
        Matplotlib Figure object.
    """
    fig = _create_figure(figsize)
    ax = fig.add_subplot(111)

    working = df.copy()
    working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
    working = working.dropna(subset=[date_col, sets_col, reps_col, weight_col])

    if working.empty:
        return _handle_insufficient_data(
            ax,
            "Insufficient data to plot weekly training volume.\n"
            "No valid workout records found.",
            "Weekly Training Volume",
        )

    working["volume_kg"] = (
        working[sets_col].astype(float)
        * working[reps_col].astype(float)
        * working[weight_col].astype(float)
    )
    working["week"] = working[date_col].dt.to_period("W")

    weekly = working.groupby("week")["volume_kg"].sum().reset_index()

    if weekly.empty:
        return _handle_insufficient_data(
            ax,
            "Insufficient data to plot weekly training volume.\n"
            "No valid weekly totals could be computed.",
            "Weekly Training Volume",
        )

    # Use Period start timestamps for plotting (timezone-naive)
    weekly["week_start"] = weekly["week"].dt.start_time

    bars = ax.bar(
        weekly["week_start"],
        weekly["volume_kg"],
        color=PRIMARY_COLOR,
        width=4,  # days
        label="Weekly Volume (kg)",
        edgecolor="white",
        linewidth=0.5,
    )

    # Add value labels on top of each bar (not color-only communication)
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            f"{height:,.0f}",
            ha="center",
            va="bottom",
            fontsize=TICK_FONTSIZE,
            color=TEXT_COLOR,
        )

    ax.set_title("Weekly Training Volume", fontsize=TITLE_FONTSIZE, color=TEXT_COLOR, pad=15)
    ax.set_ylabel("Total Volume (kg)", fontsize=LABEL_FONTSIZE, color=TEXT_COLOR)
    ax.set_xlabel("Week", fontsize=LABEL_FONTSIZE, color=TEXT_COLOR)
    _format_date_axis(ax)
    _apply_professional_style(ax)
    ax.legend(fontsize=LEGEND_FONTSIZE, loc="best", frameon=False)

    fig.tight_layout()
    return fig


# ------------------------------------------------------------------ sleep chart


def sleep_chart(
    df: pd.DataFrame,
    date_col: str = "date",
    sleep_col: str = "sleep_hours",
    figsize: tuple[float, float] = (10, 6),
) -> plt.Figure:
    """Plot daily sleep duration over time.

    Args:
        df: DataFrame with recovery log records.
        date_col: Column name for the log date.
        sleep_col: Column name for sleep hours.
        figsize: Figure size in inches.

    Returns:
        Matplotlib Figure object.
    """
    fig = _create_figure(figsize)
    ax = fig.add_subplot(111)

    working = df.copy()
    working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
    working = working.dropna(subset=[date_col, sleep_col])

    if working.empty:
        return _handle_insufficient_data(
            ax,
            "Insufficient data to plot sleep duration.\n"
            "No valid sleep records found.",
            "Sleep Duration - Daily Sleep Hours",
        )

    working = working.sort_values(date_col)

    ax.plot(
        working[date_col],
        working[sleep_col],
        color=PRIMARY_COLOR,
        linewidth=LINE_WIDTH,
        marker="o",
        markersize=MARKER_SIZE,
        label="Sleep (hours)",
    )

    # Add a reference line at 7 hours (recommended minimum)
    ax.axhline(
        7.0,
        color=SECONDARY_COLOR,
        linewidth=1,
        linestyle="--",
        alpha=0.6,
        label="Recommended minimum (7 h)",
    )

    ax.set_title("Sleep Duration - Daily Sleep Hours", fontsize=TITLE_FONTSIZE, color=TEXT_COLOR, pad=15)
    ax.set_ylabel("Sleep (hours)", fontsize=LABEL_FONTSIZE, color=TEXT_COLOR)
    ax.set_xlabel("Date", fontsize=LABEL_FONTSIZE, color=TEXT_COLOR)
    ax.set_ylim(0, max(working[sleep_col].max() * 1.1, 12))
    _format_date_axis(ax)
    _apply_professional_style(ax)
    ax.legend(fontsize=LEGEND_FONTSIZE, loc="best", frameon=False)

    fig.tight_layout()
    return fig


# ------------------------------------------------------------------ muscle-group workload


def muscle_workload_chart(
    df: pd.DataFrame,
    volume_col: str = "volume_kg",
    muscle_col: str = "muscle_group",
    figsize: tuple[float, float] = (10, 6),
) -> plt.Figure:
    """Plot training volume distribution by muscle group as a horizontal bar chart.

    Args:
        df: DataFrame with volume and muscle group columns (typically output
            of ``bulk_training_volume``).
        volume_col: Column name for per-set volume in kg.
        muscle_col: Column name for muscle group.
        figsize: Figure size in inches.

    Returns:
        Matplotlib Figure object.
    """
    fig = _create_figure(figsize)
    ax = fig.add_subplot(111)

    working = df.dropna(subset=[volume_col, muscle_col]).copy()

    if working.empty:
        return _handle_insufficient_data(
            ax,
            "Insufficient data to plot muscle-group workload.\n"
            "No valid volume or muscle-group records found.",
            "Muscle-Group Workload - Volume Distribution",
        )

    workload = (
        working.groupby(muscle_col)[volume_col]
        .sum()
        .sort_values(ascending=True)
    )

    bars = ax.barh(
        workload.index,
        workload.values,
        color=PRIMARY_COLOR,
        edgecolor="white",
        linewidth=0.5,
        label="Volume by Muscle Group (kg)",
    )

    # Add value labels at end of each bar (not color-only communication)
    for i, (muscle, volume) in enumerate(workload.items()):
        ax.text(
            volume,
            i,
            f" {volume:,.0f} kg",
            va="center",
            fontsize=TICK_FONTSIZE,
            color=TEXT_COLOR,
        )

    ax.set_title(
        "Muscle-Group Workload - Training Volume Distribution",
        fontsize=TITLE_FONTSIZE,
        color=TEXT_COLOR,
        pad=15,
    )
    ax.set_xlabel("Total Volume (kg)", fontsize=LABEL_FONTSIZE, color=TEXT_COLOR)
    ax.set_ylabel("Muscle Group", fontsize=LABEL_FONTSIZE, color=TEXT_COLOR)
    ax.grid(axis="x", color=GRID_COLOR, linewidth=0.8, alpha=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors=TEXT_COLOR, labelsize=TICK_FONTSIZE)

    fig.tight_layout()
    return fig


# ------------------------------------------------------------------ body-weight chart


def body_weight_chart(
    df: pd.DataFrame,
    date_col: str = "date",
    weight_col: str = "body_weight_kg",
    figsize: tuple[float, float] = (10, 6),
) -> plt.Figure:
    """Plot body-weight trend over time.

    Missing measurements are shown as gaps (not treated as zero).

    Args:
        df: DataFrame with recovery log records.
        date_col: Column name for the log date.
        weight_col: Column name for body weight in kg.
        figsize: Figure size in inches.

    Returns:
        Matplotlib Figure object.
    """
    fig = _create_figure(figsize)
    ax = fig.add_subplot(111)

    working = df.copy()
    working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
    working = working.dropna(subset=[date_col, weight_col])

    if working.empty:
        return _handle_insufficient_data(
            ax,
            "Insufficient data to plot body-weight trend.\n"
            "No valid body-weight records found.",
            "Body-Weight Trend",
        )

    working = working.sort_values(date_col)

    ax.plot(
        working[date_col],
        working[weight_col],
        color=PRIMARY_COLOR,
        linewidth=LINE_WIDTH,
        marker="o",
        markersize=MARKER_SIZE,
        label="Body Weight (kg)",
    )

    ax.set_title("Body-Weight Trend", fontsize=TITLE_FONTSIZE, color=TEXT_COLOR, pad=15)
    ax.set_ylabel("Body Weight (kg)", fontsize=LABEL_FONTSIZE, color=TEXT_COLOR)
    ax.set_xlabel("Date", fontsize=LABEL_FONTSIZE, color=TEXT_COLOR)
    _format_date_axis(ax)
    _apply_professional_style(ax)
    ax.legend(fontsize=LEGEND_FONTSIZE, loc="best", frameon=False)

    fig.tight_layout()
    return fig


# ------------------------------------------------------------------ RPE chart


def rpe_chart(
    df: pd.DataFrame,
    date_col: str = "date",
    rpe_col: str = "rpe",
    figsize: tuple[float, float] = (10, 6),
) -> plt.Figure:
    """Plot average RPE per session over time.

    Args:
        df: DataFrame with workout set records containing RPE values.
        date_col: Column name for the session date.
        rpe_col: Column name for RPE.
        figsize: Figure size in inches.

    Returns:
        Matplotlib Figure object.
    """
    fig = _create_figure(figsize)
    ax = fig.add_subplot(111)

    working = df.copy()
    working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
    working = working.dropna(subset=[date_col, rpe_col])

    if working.empty:
        return _handle_insufficient_data(
            ax,
            "Insufficient data to plot RPE trend.\n"
            "No valid RPE records found.",
            "RPE Trend - Average RPE Per Session",
        )

    # Average RPE per session date
    working["date_only"] = working[date_col].dt.date
    daily_rpe = working.groupby("date_only")[rpe_col].mean().reset_index()
    daily_rpe[date_col] = pd.to_datetime(daily_rpe["date_only"])

    ax.plot(
        daily_rpe[date_col],
        daily_rpe[rpe_col],
        color=PRIMARY_COLOR,
        linewidth=LINE_WIDTH,
        marker="o",
        markersize=MARKER_SIZE,
        label="Average RPE",
    )

    # Reference line at RPE 8 (high exertion)
    ax.axhline(
        8.0,
        color=SECONDARY_COLOR,
        linewidth=1,
        linestyle="--",
        alpha=0.6,
        label="High exertion (RPE 8)",
    )

    ax.set_title("RPE Trend - Average RPE Per Session", fontsize=TITLE_FONTSIZE, color=TEXT_COLOR, pad=15)
    ax.set_ylabel("Average RPE (1-10)", fontsize=LABEL_FONTSIZE, color=TEXT_COLOR)
    ax.set_xlabel("Date", fontsize=LABEL_FONTSIZE, color=TEXT_COLOR)
    ax.set_ylim(0, 11)
    _format_date_axis(ax)
    _apply_professional_style(ax)
    ax.legend(fontsize=LEGEND_FONTSIZE, loc="best", frameon=False)

    fig.tight_layout()
    return fig


# ------------------------------------------------------------------ export


def export_figure_to_png(
    fig: plt.Figure,
    filepath: str,
    dpi: int = 150,
    bbox_inches: str = "tight",
) -> None:
    """Export a Matplotlib Figure to a PNG file.

    Args:
        fig: Matplotlib Figure object to export.
        filepath: Output file path (should end with .png).
        dpi: Resolution in dots per inch.
        bbox_inches: Bounding box in inches (``'tight'`` to trim whitespace).
    """
    fig.savefig(filepath, dpi=dpi, bbox_inches=bbox_inches, facecolor="white")
