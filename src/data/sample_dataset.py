"""Sample fitness dataset used throughout the project.

Phase 1 deliverable: a small, realistic dataset built in pure Python and loaded
into pandas DataFrames so it can be inspected, manipulated and analysed.

The data mirrors the future SQLite tables:

* workout set records  -> ``workout_sets`` (one row per exercise in a session)
* recovery records     -> ``recovery_logs`` (one row per calendar day)

Two deliberate behaviours to be aware of:

* ``session_duration_min`` is repeated on every set row of the same session,
  because the duration belongs to the session, not to an individual exercise.
  Never sum this column across rows.
* Bodyweight movements (e.g. pull-ups) are stored with ``weight_kg = 0.0`` for
  now. Added weight is not modelled yet.

Pass ``include_anomalies=False`` to get a clean dataset for later phases.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

# The dataset starts on a Monday and covers five consecutive weeks.
START_DATE = date(2026, 10, 5)
NUM_WEEKS = 5

# From this week (0-indexed) onward every exercise gets one extra set. This
# creates a sharp jump in weekly volume for the workload detector to find.
VOLUME_SPIKE_WEEK = 3
EXTRA_SETS_PER_EXERCISE = 1

WORKOUT_COLUMNS = [
    "date",
    "week",
    "exercise",
    "muscle_group",
    "equipment",
    "sets",
    "reps",
    "weight_kg",
    "rpe",
    "session_duration_min",
]

RECOVERY_COLUMNS = [
    "date",
    "week",
    "day_type",
    "sleep_hours",
    "body_weight_kg",
    "soreness",
    "energy",
]


@dataclass(frozen=True)
class Exercise:
    """Static description of an exercise used to generate sample sessions."""

    name: str
    muscle_group: str
    equipment: str
    base_weight: float
    reps: int
    weekly_increment: float
    sets: int
    rpe_offset: float = 0.0
    # Week index at which progression stops. None means it keeps progressing.
    plateau_week: int | None = None


EXERCISES: dict[str, Exercise] = {
    "Bench Press": Exercise(
        name="Bench Press",
        muscle_group="Chest",
        equipment="Barbell",
        base_weight=80.0,
        reps=5,
        weekly_increment=2.5,
        sets=4,
        rpe_offset=0.3,
        plateau_week=2,
    ),
    "Overhead Press": Exercise(
        name="Overhead Press",
        muscle_group="Shoulders",
        equipment="Barbell",
        base_weight=45.0,
        reps=8,
        weekly_increment=2.5,
        sets=3,
        rpe_offset=0.5,
    ),
    "Triceps Pushdown": Exercise(
        name="Triceps Pushdown",
        muscle_group="Arms",
        equipment="Cable",
        base_weight=30.0,
        reps=12,
        weekly_increment=2.5,
        sets=3,
        rpe_offset=0.0,
    ),
    "Back Squat": Exercise(
        name="Back Squat",
        muscle_group="Legs",
        equipment="Barbell",
        base_weight=110.0,
        reps=5,
        weekly_increment=5.0,
        sets=4,
        rpe_offset=0.4,
    ),
    "Romanian Deadlift": Exercise(
        name="Romanian Deadlift",
        muscle_group="Legs",
        equipment="Barbell",
        base_weight=90.0,
        reps=8,
        weekly_increment=2.5,
        sets=3,
        rpe_offset=0.2,
    ),
    "Leg Press": Exercise(
        name="Leg Press",
        muscle_group="Legs",
        equipment="Machine",
        base_weight=150.0,
        reps=12,
        weekly_increment=5.0,
        sets=3,
        rpe_offset=-0.2,
    ),
    "Deadlift": Exercise(
        name="Deadlift",
        muscle_group="Back",
        equipment="Barbell",
        base_weight=140.0,
        reps=5,
        weekly_increment=5.0,
        sets=3,
        rpe_offset=0.6,
    ),
    "Barbell Row": Exercise(
        name="Barbell Row",
        muscle_group="Back",
        equipment="Barbell",
        base_weight=70.0,
        reps=8,
        weekly_increment=2.5,
        sets=4,
        rpe_offset=0.2,
    ),
    "Pull-Up": Exercise(
        name="Pull-Up",
        muscle_group="Back",
        equipment="Bodyweight",
        base_weight=0.0,
        reps=8,
        weekly_increment=0.0,
        sets=3,
        rpe_offset=0.7,
    ),
    "Biceps Curl": Exercise(
        name="Biceps Curl",
        muscle_group="Arms",
        equipment="Dumbbell",
        base_weight=14.0,
        reps=10,
        weekly_increment=1.0,
        sets=3,
        rpe_offset=-0.1,
    ),
}

# Weekday index (Monday == 0) -> exercises trained that day.
TRAINING_DAYS: dict[int, list[str]] = {
    0: ["Bench Press", "Overhead Press", "Triceps Pushdown"],
    1: ["Back Squat", "Romanian Deadlift", "Leg Press"],
    3: ["Deadlift", "Barbell Row", "Pull-Up"],
    5: ["Bench Press", "Back Squat", "Biceps Curl"],
}


def _noise(seed: int, spread: float) -> float:
    """Deterministic pseudo-noise so the dataset is identical on every run."""
    return ((seed * 37) % 11 - 5) / 5.0 * spread


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _session_date(week: int, weekday: int) -> date:
    return START_DATE + timedelta(weeks=week, days=weekday)


def build_workout_sets(include_anomalies: bool = True) -> pd.DataFrame:
    """Build one row per exercise performed in each session.

    Training load ramps up over the five weeks, RPE drifts upward, the bench
    press stops progressing after week 3, and weeks 4-5 add one extra set to
    every exercise. That combination gives later phases (plateau, workload and
    fatigue detection) something meaningful to find.
    """
    rows: list[dict] = []

    for week in range(NUM_WEEKS):
        for weekday, exercise_names in TRAINING_DAYS.items():
            session_date = _session_date(week, weekday)
            duration = 65 + 5 * weekday + int(3 * week) + (weekday == 5) * 5

            for name in exercise_names:
                exercise = EXERCISES[name]
                progression_week = (
                    week
                    if exercise.plateau_week is None
                    else min(week, exercise.plateau_week)
                )

                weight = exercise.base_weight + exercise.weekly_increment * progression_week
                weight = round(weight * 2) / 2  # nearest loadable 0.5 kg
                rpe = 7.0 + 0.3 * week + exercise.rpe_offset
                rpe = round(_clamp(rpe, 5.0, 9.5) * 2) / 2
                sets = exercise.sets
                if week >= VOLUME_SPIKE_WEEK:
                    sets += EXTRA_SETS_PER_EXERCISE

                rows.append(
                    {
                        "date": session_date,
                        "week": week + 1,
                        "exercise": name,
                        "muscle_group": exercise.muscle_group,
                        "equipment": exercise.equipment,
                        "sets": sets,
                        "reps": exercise.reps,
                        "weight_kg": weight,
                        "rpe": rpe,
                        "session_duration_min": duration,
                    }
                )

    if include_anomalies:
        rows.extend(_workout_anomalies(rows))

    return pd.DataFrame(rows, columns=WORKOUT_COLUMNS)


def _workout_anomalies(rows: list[dict]) -> list[dict]:
    """Deliberately dirty rows for the Phase 2 validation module to catch."""
    duplicate = dict(rows[0])                      # exact duplicate record
    negative_reps = dict(rows[1])                  # impossible repetition count
    negative_reps["reps"] = -8
    invalid_rpe = dict(rows[2])                    # RPE must be 1-10
    invalid_rpe["rpe"] = 15.0
    missing_weight = dict(rows[3])                 # weight not recorded
    missing_weight["weight_kg"] = None
    return [duplicate, negative_reps, invalid_rpe, missing_weight]


def build_recovery_logs(include_anomalies: bool = True) -> pd.DataFrame:
    """Build one recovery row per calendar day, including rest days.

    Sleep and energy trend down while soreness trends up, so the recovery
    analysis and fatigue detection phases have a worsening pattern to report.
    """
    rows: list[dict] = []
    total_days = NUM_WEEKS * 7
    training_weekdays = set(TRAINING_DAYS)

    for day_index in range(total_days):
        current = START_DATE + timedelta(days=day_index)
        week = day_index // 7

        sleep = 7.6 - 0.28 * week + _noise(day_index, 0.45)
        soreness = 3.0 + 0.85 * week + _noise(day_index + 3, 1.0)
        energy = 8.0 - 0.55 * week + _noise(day_index + 7, 0.8)
        body_weight = 78.4 + 0.12 * week + _noise(day_index + 11, 0.4)

        rows.append(
            {
                "date": current,
                "week": week + 1,
                "day_type": "training" if current.weekday() in training_weekdays else "rest",
                "sleep_hours": round(_clamp(sleep, 4.5, 9.0), 1),
                "body_weight_kg": round(_clamp(body_weight, 70.0, 95.0), 1),
                "soreness": round(_clamp(soreness, 1.0, 10.0)),
                "energy": round(_clamp(energy, 1.0, 10.0)),
            }
        )

    if include_anomalies:
        rows[9]["sleep_hours"] = None    # missing sleep entry
        rows[20]["energy"] = 11          # energy must be 1-10

    return pd.DataFrame(rows, columns=RECOVERY_COLUMNS)


def load_dataset(include_anomalies: bool = True) -> dict[str, pd.DataFrame]:
    """Return both sample tables in one dict."""
    return {
        "workout_sets": build_workout_sets(include_anomalies=include_anomalies),
        "recovery_logs": build_recovery_logs(include_anomalies=include_anomalies),
    }
