"""Cleaning pipeline for workout and recovery records.

Phase 2 deliverable. The pipeline is deliberately explicit and logged:

1. convert ``date`` to datetime64
2. drop exact duplicate rows
3. apply the chosen missing-value strategy (``keep`` / ``drop`` / ``median``)
4. validate the remaining rows
5. split off rows that have ``error`` issues (warnings stay in the data)

Note: with ``missing_strategy="keep"``, a row that is missing a required field
is still rejected in step 5, because validation treats missing required fields
as errors. Use ``drop`` or ``median`` when you want a guaranteed clean frame.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from src.data.validation import (
    RECOVERY_METRIC_COLUMNS,
    WORKOUT_REQUIRED_COLUMNS,
    Issue,
    validate_recovery_logs,
    validate_workout_sets,
)

MissingStrategy = Literal["keep", "drop", "median"]
MISSING_STRATEGIES: tuple[str, ...] = ("keep", "drop", "median")


@dataclass
class CleaningLog:
    """What the pipeline did, in order."""

    rows_in: int
    rows_out: int = 0
    actions: list[str] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    @property
    def rows_removed(self) -> int:
        return self.rows_in - self.rows_out

    def summary(self) -> str:
        lines = [f"rows in: {self.rows_in} | rows out: {self.rows_out} | removed: {self.rows_removed}"]
        lines.extend(f"  - {action}" for action in self.actions)
        errors = sum(1 for issue in self.issues if issue.severity == "error")
        warnings = sum(1 for issue in self.issues if issue.severity == "warning")
        lines.append(f"  - validation: {errors} error(s), {warnings} warning(s)")
        return "\n".join(lines)


@dataclass
class CleaningResult:
    """Cleaned data, rejected rows, and the log that explains both."""

    data: pd.DataFrame
    rejected: pd.DataFrame
    log: CleaningLog


def convert_dates(df: pd.DataFrame, column: str = "date") -> pd.DataFrame:
    """Return a copy with the date column parsed to datetime64 (invalid -> NaT)."""
    result = df.copy()
    if column in result.columns:
        result[column] = pd.to_datetime(result[column], errors="coerce")
    return result


def drop_exact_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy without exact duplicate rows, keeping the first occurrence."""
    return df.drop_duplicates(keep="first").copy()


def apply_missing_strategy(
    df: pd.DataFrame, columns: list[str], strategy: MissingStrategy
) -> pd.DataFrame:
    """Handle missing values in ``columns`` according to ``strategy``."""
    if strategy not in MISSING_STRATEGIES:
        raise ValueError(f"unknown strategy {strategy!r}; expected one of {MISSING_STRATEGIES}")

    if strategy == "keep":
        return df.copy()

    present = [column for column in columns if column in df.columns]
    if strategy == "drop":
        return df.dropna(subset=present).copy()

    result = df.copy()
    for column in present:
        if not pd.api.types.is_numeric_dtype(result[column]):
            continue
        median = result[column].median()
        if pd.notna(median):
            result[column] = result[column].fillna(median)
    return result


def split_errors(df: pd.DataFrame, issues: list[Issue]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split rows into (valid, rejected) using ``error`` issues only."""
    bad_rows = {issue.row for issue in issues if issue.severity == "error" and issue.row is not None}
    mask = df.index.isin(bad_rows)
    return df[~mask].copy(), df[mask].copy()


def _clean_table(
    df: pd.DataFrame,
    *,
    label: str,
    missing_columns: list[str],
    validator,
    missing_strategy: MissingStrategy,
) -> CleaningResult:
    log = CleaningLog(rows_in=len(df))
    working = convert_dates(df)
    if "date" in working.columns:
        log.actions.append("parsed 'date' to datetime64 (invalid dates become NaT)")

    before = len(working)
    working = drop_exact_duplicates(working)
    if len(working) != before:
        log.actions.append(f"removed {before - len(working)} exact duplicate row(s)")

    before = len(working)
    working = apply_missing_strategy(working, missing_columns, missing_strategy)
    if missing_strategy == "drop" and len(working) != before:
        log.actions.append(f"dropped {before - len(working)} row(s) with missing values")
    elif missing_strategy == "median":
        log.actions.append("filled missing numeric values with the column median")
    else:
        log.actions.append("left missing values untouched (strategy='keep')")

    issues = validator(working)
    working, rejected = split_errors(working, issues)
    if len(rejected):
        log.actions.append(f"rejected {len(rejected)} row(s) with validation errors")

    log.issues = issues
    log.rows_out = len(working)
    log.actions.append(f"'{label}' cleaned")
    return CleaningResult(
        data=working.reset_index(drop=True),
        rejected=rejected.reset_index(drop=True),
        log=log,
    )


def clean_workout_sets(
    df: pd.DataFrame, missing_strategy: MissingStrategy = "keep"
) -> CleaningResult:
    """Clean workout set records."""
    return _clean_table(
        df,
        label="workout_sets",
        missing_columns=WORKOUT_REQUIRED_COLUMNS,
        validator=validate_workout_sets,
        missing_strategy=missing_strategy,
    )


def clean_recovery_logs(
    df: pd.DataFrame, missing_strategy: MissingStrategy = "keep"
) -> CleaningResult:
    """Clean recovery logs.

    Missing metrics are warnings, so with ``strategy="keep"`` those rows stay in
    the data with NaN values.
    """
    return _clean_table(
        df,
        label="recovery_logs",
        missing_columns=RECOVERY_METRIC_COLUMNS,
        validator=validate_recovery_logs,
        missing_strategy=missing_strategy,
    )
