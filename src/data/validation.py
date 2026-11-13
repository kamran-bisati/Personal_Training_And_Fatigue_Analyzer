"""Input validation for workout and recovery records.

Phase 2 deliverable. Every function is pure: it takes a DataFrame and returns a
list of ``Issue`` objects. Nothing is modified, nothing is deleted, nothing is
raised. The caller decides what to do with the findings.

Two severities exist:

* ``error``   - the record cannot be trusted and should be rejected
* ``warning`` - suspicious but plausible, keep it and show it to the user

Outliers are always warnings. They are never used to silently delete data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

import pandas as pd

Severity = Literal["error", "warning"]

MIN_DATE = date(2020, 1, 1)

WORKOUT_REQUIRED_COLUMNS = ["date", "exercise", "sets", "reps", "weight_kg", "rpe"]
RECOVERY_REQUIRED_COLUMNS = ["date"]
RECOVERY_METRIC_COLUMNS = ["sleep_hours", "body_weight_kg", "soreness", "energy"]

WORKOUT_RANGES: dict[str, tuple[float, float]] = {
    "sets": (1, 20),
    "reps": (1, 100),
    "weight_kg": (0, 500),
    "rpe": (1, 10),
}

RECOVERY_RANGES: dict[str, tuple[float, float]] = {
    "sleep_hours": (0, 24),
    "body_weight_kg": (30, 300),
    "soreness": (1, 10),
    "energy": (1, 10),
}

MAX_SINGLE_RECORD_REPS = 200   # sets * reps above this is implausible
WEIGHT_JUMP_KG = 3.0           # day-to-day body-weight change
UNUSUAL_SLEEP_HOURS = (3.0, 12.0)


@dataclass(frozen=True)
class Issue:
    """A single validation finding."""

    row: int | None
    column: str | None
    code: str
    message: str
    severity: Severity = "error"

    def __str__(self) -> str:
        location = f"row {self.row}" if self.row is not None else "table"
        column = self.column or "-"
        return f"[{self.severity.upper()}] {location} | {column} | {self.code}: {self.message}"


def issues_to_frame(issues: list[Issue]) -> pd.DataFrame:
    """Return issues as a DataFrame for printing or display."""
    return pd.DataFrame(
        [
            {
                "row": issue.row,
                "column": issue.column,
                "severity": issue.severity,
                "code": issue.code,
                "message": issue.message,
            }
            for issue in issues
        ],
        columns=["row", "column", "severity", "code", "message"],
    )


def has_errors(issues: list[Issue]) -> bool:
    return any(issue.severity == "error" for issue in issues)


def _check_required_columns(
    df: pd.DataFrame, required: list[str], label: str, issues: list[Issue]
) -> None:
    for column in required:
        if column not in df.columns:
            issues.append(
                Issue(
                    row=None,
                    column=column,
                    code="missing_column",
                    message=f"{label}: required column '{column}' is missing",
                )
            )


def _check_dates(df: pd.DataFrame, label: str, issues: list[Issue]) -> None:
    if "date" not in df.columns:
        return

    parsed = pd.to_datetime(df["date"], errors="coerce")
    for index, raw_value in df["date"].items():
        parsed_value = parsed.loc[index]
        if pd.isna(parsed_value):
            issues.append(
                Issue(index, "date", "date_invalid", f"{label}: unparseable date {raw_value!r}")
            )
            continue

        day = parsed_value.date()
        if day > date.today():
            issues.append(
                Issue(index, "date", "date_future", f"{label}: date {day} is in the future")
            )
        elif day < MIN_DATE:
            issues.append(
                Issue(
                    index,
                    "date",
                    "date_too_old",
                    f"{label}: date {day} is before the supported minimum ({MIN_DATE})",
                )
            )


def _check_missing(df: pd.DataFrame, columns: list[str], label: str, issues: list[Issue], severity: Severity) -> None:
    for column in columns:
        if column not in df.columns:
            continue
        for index in df.index[df[column].isna()]:
            issues.append(
                Issue(
                    index,
                    column,
                    "missing_value",
                    f"{label}: {column} is empty",
                    severity,
                )
            )


def _check_numeric(
    df: pd.DataFrame, columns: list[str], label: str, issues: list[Issue]
) -> dict[str, pd.Series]:
    """Flag non-numeric values and return the converted columns."""
    converted: dict[str, pd.Series] = {}
    for column in columns:
        if column not in df.columns:
            continue
        values = pd.to_numeric(df[column], errors="coerce")
        converted[column] = values
        for index in df.index:
            raw_value = df.at[index, column]
            if pd.isna(raw_value):
                continue
            if pd.isna(values.loc[index]):
                issues.append(
                    Issue(
                        index,
                        column,
                        "type_invalid",
                        f"{label}: {column} must be numeric, got {raw_value!r}",
                    )
                )
    return converted


def _check_ranges(
    df: pd.DataFrame,
    converted: dict[str, pd.Series],
    ranges: dict[str, tuple[float, float]],
    label: str,
    issues: list[Issue],
) -> None:
    for column, (low, high) in ranges.items():
        if column not in converted:
            continue
        for index, value in converted[column].items():
            if pd.isna(value):
                continue
            if not low <= value <= high:
                issues.append(
                    Issue(
                        index,
                        column,
                        "range_invalid",
                        f"{label}: {column}={value:g} is outside {low:g}-{high:g}",
                    )
                )


def _check_integers(
    converted: dict[str, pd.Series], columns: list[str], label: str, issues: list[Issue]
) -> None:
    for column in columns:
        if column not in converted:
            continue
        for index, value in converted[column].items():
            if pd.isna(value):
                continue
            if abs(value - round(value)) > 1e-9:
                issues.append(
                    Issue(
                        index,
                        column,
                        "not_integer",
                        f"{label}: {column}={value:g} should be a whole number",
                        "warning",
                    )
                )


def _check_rpe_step(converted: dict[str, pd.Series], label: str, issues: list[Issue]) -> None:
    values = converted.get("rpe")
    if values is None:
        return
    for index, value in values.items():
        if pd.isna(value):
            continue
        if abs(value * 2 - round(value * 2)) > 1e-9:
            issues.append(
                Issue(
                    index,
                    "rpe",
                    "rpe_step",
                    f"{label}: RPE={value:g} is not a multiple of 0.5",
                    "warning",
                )
            )


def _check_duplicate_rows(df: pd.DataFrame, label: str, issues: list[Issue]) -> None:
    duplicated = df.duplicated(keep="first")
    for index in df.index[duplicated]:
        issues.append(
            Issue(index, None, "duplicate_row", f"{label}: row is an exact duplicate of an earlier row", "warning")
        )


def _flag_outlier_group(
    values: pd.Series,
    column: str,
    label: str,
    issues: list[Issue],
    multiplier: float,
) -> None:
    clean = values.dropna()
    if len(clean) < 4:
        return

    q1, q3 = clean.quantile([0.25, 0.75])
    spread = q3 - q1
    if spread == 0:
        return

    low, high = q1 - multiplier * spread, q3 + multiplier * spread
    for index, value in clean.items():
        if value < low or value > high:
            issues.append(
                Issue(
                    index,
                    column,
                    "outlier",
                    f"{label}: {column}={value:g} is outside the typical range ({low:.1f} to {high:.1f})",
                    "warning",
                )
            )


def _flag_outliers(
    values: pd.Series,
    column: str,
    label: str,
    issues: list[Issue],
    multiplier: float = 1.5,
    group_key: pd.Series | None = None,
) -> None:
    """Flag values outside the IQR bounds, optionally per group.

    Grouping matters for training volume: a leg press set is legitimately
    heavier than a curl set, so it must be compared with its own history.
    """
    if group_key is None:
        _flag_outlier_group(values, column, label, issues, multiplier)
        return

    frame = pd.DataFrame({"value": values, "group": group_key})
    for _, group in frame.groupby("group", dropna=False):
        _flag_outlier_group(group["value"], column, label, issues, multiplier)


def validate_workout_sets(df: pd.DataFrame) -> list[Issue]:
    """Validate workout set records. Returns errors and warnings."""
    label = "workout_sets"
    issues: list[Issue] = []

    _check_required_columns(df, WORKOUT_REQUIRED_COLUMNS, label, issues)
    _check_dates(df, label, issues)

    present = [c for c in WORKOUT_REQUIRED_COLUMNS if c in df.columns]
    _check_missing(df, present, label, issues, severity="error")

    converted = _check_numeric(
        df, ["sets", "reps", "weight_kg", "rpe", "session_duration_min"], label, issues
    )
    _check_ranges(df, converted, WORKOUT_RANGES, label, issues)
    _check_integers(converted, ["sets", "reps"], label, issues)
    _check_rpe_step(converted, label, issues)
    _check_duplicate_rows(df, label, issues)

    if {"date", "exercise"}.issubset(df.columns):
        repeated = df.duplicated(subset=["date", "exercise"], keep="first")
        for index in df.index[repeated]:
            issues.append(
                Issue(
                    index,
                    "exercise",
                    "duplicate_session_exercise",
                    f"{label}: '{df.at[index, 'exercise']}' already recorded on {df.at[index, 'date']}",
                    "warning",
                )
            )

    if {"equipment", "weight_kg"}.issubset(df.columns):
        zero_barbell = (df["equipment"] == "Barbell") & (converted["weight_kg"] == 0)
        for index in df.index[zero_barbell]:
            issues.append(
                Issue(
                    index,
                    "weight_kg",
                    "zero_weight_barbell",
                    f"{label}: barbell exercise recorded with 0 kg",
                    "warning",
                )
            )

    if {"sets", "reps"}.issubset(converted):
        total_reps = converted["sets"] * converted["reps"]
        for index, value in total_reps.items():
            if pd.notna(value) and value > MAX_SINGLE_RECORD_REPS:
                issues.append(
                    Issue(
                        index,
                        "reps",
                        "implausible_volume",
                        f"{label}: sets x reps = {value:g} in one record is implausible",
                        "warning",
                    )
                )

    if {"sets", "reps", "weight_kg"}.issubset(converted):
        volume = converted["sets"] * converted["reps"] * converted["weight_kg"]
        _flag_outliers(
            volume,
            "volume",
            label,
            issues,
            group_key=df["exercise"] if "exercise" in df.columns else None,
        )

    return issues


def validate_recovery_logs(df: pd.DataFrame) -> list[Issue]:
    """Validate daily recovery records. Missing metrics are warnings, not errors."""
    label = "recovery_logs"
    issues: list[Issue] = []

    _check_required_columns(df, RECOVERY_REQUIRED_COLUMNS, label, issues)
    _check_dates(df, label, issues)

    if "date" in df.columns:
        _check_missing(df, ["date"], label, issues, severity="error")
        repeated = df.duplicated(subset=["date"], keep="first")
        for index in df.index[repeated]:
            issues.append(
                Issue(
                    index,
                    "date",
                    "duplicate_date",
                    f"{label}: a record for {df.at[index, 'date']} already exists",
                    "warning",
                )
            )

    metrics = [c for c in RECOVERY_METRIC_COLUMNS if c in df.columns]
    _check_missing(df, metrics, label, issues, severity="warning")

    converted = _check_numeric(df, RECOVERY_METRIC_COLUMNS, label, issues)
    _check_ranges(df, converted, RECOVERY_RANGES, label, issues)
    _check_integers(converted, ["soreness", "energy"], label, issues)
    _check_duplicate_rows(df, label, issues)

    if "sleep_hours" in converted:
        low, high = UNUSUAL_SLEEP_HOURS
        for index, value in converted["sleep_hours"].items():
            if pd.notna(value) and (value < low or value > high):
                issues.append(
                    Issue(
                        index,
                        "sleep_hours",
                        "unusual_sleep",
                        f"{label}: {value:g} h of sleep is unusual",
                        "warning",
                    )
                )
        _flag_outliers(converted["sleep_hours"], "sleep_hours", label, issues)

    if {"date", "body_weight_kg"}.issubset(df.columns):
        weights = pd.DataFrame(
            {
                "date": pd.to_datetime(df["date"], errors="coerce"),
                "weight": converted.get("body_weight_kg", pd.to_numeric(df["body_weight_kg"], errors="coerce")),
            }
        ).dropna()
        weights = weights.sort_values("date")
        changes = weights["weight"].diff().abs()
        for index, change in changes.items():
            if pd.notna(change) and change > WEIGHT_JUMP_KG:
                issues.append(
                    Issue(
                        index,
                        "body_weight_kg",
                        "weight_jump",
                        f"{label}: body weight changed by {change:.1f} kg since the previous entry",
                        "warning",
                    )
                )

    return issues
