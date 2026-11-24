"""Program management: custom splits, PPL / Upper-Lower templates and day/exercise assignment.

Builds on the Phase 3 CRUD tables (training_programs, program_days,
program_exercises) and adds preset templates plus convenience helpers.
"""

from __future__ import annotations

from typing import Optional

from database import repository as repo
from database.db_setup import get_connection


class ProgramManager:
    """Higher-level training program and schedule management."""

    def __init__(self, connection=None) -> None:
        self._owns_connection = connection is None
        self.conn = connection or get_connection()

    def close(self) -> None:
        if self._owns_connection:
            self.conn.close()

    def __enter__(self) -> "ProgramManager":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # ------------------------------------------------------------------ programs

    def create_program(
        self,
        user_id: int,
        name: str,
        split_type: str,
        is_active: int = 0,
    ) -> int:
        """Create a training program for a user.

        ``split_type`` is typically one of: 'PPL', 'Upper/Lower', 'Full Body', 'Custom'.
        """
        return repo.create_program(
            self.conn,
            user_id=user_id,
            name=name,
            split_type=split_type,
            is_active=is_active,
        )

    def get_program(self, program_id: int) -> Optional[dict]:
        row = repo.get_program(self.conn, program_id)
        return dict(row) if row else None

    def list_programs(self, user_id: int) -> list[dict]:
        rows = repo.list_programs_by_user(self.conn, user_id)
        return [dict(row) for row in rows]

    def set_active_program(self, user_id: int, program_id: int) -> None:
        """Deactivate all of a user's programs, then activate the chosen one."""
        self.conn.execute(
            "UPDATE training_programs SET is_active = 0 WHERE user_id = ?", (user_id,)
        )
        self.conn.execute(
            "UPDATE training_programs SET is_active = 1 WHERE id = ? AND user_id = ?",
            (program_id, user_id),
        )
        self.conn.commit()

    def delete_program(self, program_id: int) -> int:
        return repo.delete_program(self.conn, program_id) if hasattr(repo, "delete_program") else 0

    # ------------------------------------------------------------------ days

    def add_day(self, program_id: int, day_name: str, day_order: int) -> int:
        return repo.create_program_day(
            self.conn, program_id=program_id, day_name=day_name, day_order=day_order
        )

    def get_program_structure(self, program_id: int) -> list[dict]:
        rows = repo.list_program_days_with_exercises(self.conn, program_id)
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------ exercises in days

    def assign_exercise(
        self,
        program_day_id: int,
        exercise_id: int,
        target_sets: Optional[int] = None,
        target_reps: Optional[int] = None,
        target_weight_kg: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> int:
        return repo.add_program_exercise(
            self.conn,
            program_day_id=program_day_id,
            exercise_id=exercise_id,
            target_sets=target_sets,
            target_reps=target_reps,
            target_weight_kg=target_weight_kg,
            notes=notes,
        )

    # ------------------------------------------------------------------ templates

    PPL_TEMPLATE: dict[str, list[dict]] = {
        "Push": [
            {"name": "Bench Press", "target_sets": 4, "target_reps": 5},
            {"name": "Overhead Press", "target_sets": 3, "target_reps": 8},
            {"name": "Triceps Pushdown", "target_sets": 3, "target_reps": 12},
        ],
        "Pull": [
            {"name": "Deadlift", "target_sets": 3, "target_reps": 5},
            {"name": "Barbell Row", "target_sets": 4, "target_reps": 8},
            {"name": "Pull-Up", "target_sets": 3, "target_reps": 8},
        ],
        "Legs": [
            {"name": "Back Squat", "target_sets": 4, "target_reps": 5},
            {"name": "Romanian Deadlift", "target_sets": 3, "target_reps": 8},
            {"name": "Leg Press", "target_sets": 3, "target_reps": 12},
        ],
    }

    UPPER_LOWER_TEMPLATE: dict[str, list[dict]] = {
        "Upper A": [
            {"name": "Bench Press", "target_sets": 4, "target_reps": 5},
            {"name": "Overhead Press", "target_sets": 3, "target_reps": 8},
            {"name": "Barbell Row", "target_sets": 4, "target_reps": 8},
            {"name": "Biceps Curl", "target_sets": 3, "target_reps": 10},
            {"name": "Triceps Pushdown", "target_sets": 3, "target_reps": 12},
        ],
        "Lower A": [
            {"name": "Back Squat", "target_sets": 4, "target_reps": 5},
            {"name": "Romanian Deadlift", "target_sets": 3, "target_reps": 8},
            {"name": "Leg Press", "target_sets": 3, "target_reps": 12},
            {"name": "Deadlift", "target_sets": 3, "target_reps": 5},
            {"name": "Pull-Up", "target_sets": 3, "target_reps": 8},
        ],
        "Upper B": [
            {"name": "Bench Press", "target_sets": 4, "target_reps": 8},
            {"name": "Overhead Press", "target_sets": 3, "target_reps": 10},
            {"name": "Barbell Row", "target_sets": 3, "target_reps": 10},
            {"name": "Biceps Curl", "target_sets": 3, "target_reps": 12},
            {"name": "Triceps Pushdown", "target_sets": 4, "target_reps": 10},
        ],
        "Lower B": [
            {"name": "Back Squat", "target_sets": 3, "target_reps": 8},
            {"name": "Romanian Deadlift", "target_sets": 3, "target_reps": 10},
            {"name": "Leg Press", "target_sets": 4, "target_reps": 10},
            {"name": "Deadlift", "target_sets": 3, "target_reps": 5},
            {"name": "Pull-Up", "target_sets": 3, "target_reps": 10},
        ],
    }

    def create_from_template(
        self,
        user_id: int,
        name: str,
        split_type: str,
        template: str = "PPL",
    ) -> int:
        """Create a program from a built-in template and return the program id.

        ``template`` is either ``'PPL'`` (3 days) or ``'Upper/Lower'`` (4 days).
        """
        templates = {
            "PPL": self.PPL_TEMPLATE,
            "Upper/Lower": self.UPPER_LOWER_TEMPLATE,
        }
        if template not in templates:
            raise ValueError(f"unknown template {template!r}; expected 'PPL' or 'Upper/Lower'")

        program_id = self.create_program(
            user_id=user_id, name=name, split_type=split_type, is_active=1
        )

        exercise_cache = {
            row["name"]: row["id"] for row in repo.list_exercises(self.conn)
        }

        for day_order, (day_name, exercises) in enumerate(templates[template].items(), start=1):
            day_id = self.add_day(
                program_id=program_id, day_name=day_name, day_order=day_order
            )
            for exercise_plan in exercises:
                exercise_id = exercise_cache.get(exercise_plan["name"])
                if exercise_id is None:
                    continue
                self.assign_exercise(
                    program_day_id=day_id,
                    exercise_id=exercise_id,
                    target_sets=exercise_plan.get("target_sets"),
                    target_reps=exercise_plan.get("target_reps"),
                )

        return program_id
