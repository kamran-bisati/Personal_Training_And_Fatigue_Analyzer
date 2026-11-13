"""Workout management: sessions and sets on top of the Phase 3 CRUD layer.

Integrates Phase 2 validation so nothing is written to SQLite unless it passes
the validation rules. Exposes session creation, set logging, history and
personal records through one manager object.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd

from database import repository as repo
from database.db_setup import get_connection
from src.data.validation import validate_workout_sets, issues_to_frame


class WorkoutManager:
    """Higher-level workout session and set management."""

    def __init__(self, connection=None) -> None:
        self._owns_connection = connection is None
        self.conn = connection or get_connection()

    def close(self) -> None:
        if self._owns_connection:
            self.conn.close()

    def __enter__(self) -> "WorkoutManager":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # ------------------------------------------------------------------ sessions

    def create_session(
        self,
        user_id: int,
        session_date: str,
        duration_min: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> int:
        """Create a workout session for a user on a date (YYYY-MM-DD).

        Raises sqlite3.IntegrityError if the user already has a session that day.
        """
        return repo.create_session(
            self.conn,
            user_id=user_id,
            session_date=session_date,
            duration_min=duration_min,
            notes=notes,
        )

    def get_session(self, session_id: int) -> Optional[dict]:
        row = repo.get_session(self.conn, session_id)
        return dict(row) if row else None

    def list_sessions(self, user_id: int, limit: Optional[int] = None) -> list[dict]:
        rows = repo.list_sessions_by_user(self.conn, user_id, limit=limit)
        return [dict(row) for row in rows]

    def delete_session(self, session_id: int) -> int:
        return repo.delete_session(self.conn, session_id)

    # ------------------------------------------------------------------ sets

    def add_sets_from_dataframe(
        self,
        session_id: int,
        sets_df: pd.DataFrame,
    ) -> tuple[int, list]:
        """Validate and insert multiple sets for a session from a DataFrame.

        Returns ``(inserted_count, issues)`` where ``issues`` are validation
        warnings (non-fatal). Rows that fail validation are skipped but reported.
        """
        if sets_df.empty:
            return 0, []

        issues = validate_workout_sets(sets_df)
        error_rows = {
            issue.row for issue in issues if issue.severity == "error" and issue.row is not None
        }

        inserted = 0
        for idx, row in sets_df.iterrows():
            if idx in error_rows:
                continue

            exercise_name = row.get("exercise")
            exercise = repo.get_exercise_by_name(self.conn, exercise_name)
            if exercise is None:
                issues.append(
                    type(
                        "Issue",
                        (),
                        {
                            "row": idx,
                            "column": "exercise",
                            "code": "exercise_not_found",
                            "message": f"exercise {exercise_name!r} not in library",
                            "severity": "warning",
                        },
                    )()
                )
                continue

            repo.add_set(
                self.conn,
                session_id=session_id,
                exercise_id=exercise["id"],
                set_number=int(row.get("set_number", idx + 1)),
                reps=int(row["reps"]),
                weight_kg=float(row["weight_kg"]),
                rpe=(float(row["rpe"]) if pd.notna(row.get("rpe")) else None),
            )
            inserted += 1

        return inserted, issues

    def add_set(
        self,
        session_id: int,
        exercise_id: int,
        set_number: int,
        reps: int,
        weight_kg: float,
        rpe: Optional[float] = None,
    ) -> int:
        return repo.add_set(
            self.conn,
            session_id=session_id,
            exercise_id=exercise_id,
            set_number=set_number,
            reps=reps,
            weight_kg=weight_kg,
            rpe=rpe,
        )

    def get_sets_for_session(self, session_id: int) -> list[dict]:
        rows = repo.get_sets_for_session(self.conn, session_id)
        return [dict(row) for row in rows]

    def delete_set(self, set_id: int) -> int:
        return repo.delete_set(self.conn, set_id)

    # ------------------------------------------------------------------ history & records

    def workout_history(self, user_id: int) -> list[dict]:
        rows = repo.workout_history(self.conn, user_id)
        return [dict(row) for row in rows]

    def personal_records(self, user_id: int, exercise_id: int) -> Optional[dict]:
        rows = repo.personal_records(self.conn, user_id, exercise_id)
        return dict(rows[0]) if rows else None

    def session_exists_on_date(self, user_id: int, session_date: str) -> bool:
        sessions = self.list_sessions(user_id)
        return any(s["session_date"] == session_date for s in sessions)
