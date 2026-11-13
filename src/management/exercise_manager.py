"""Exercise management: library operations on top of the Phase 3 CRUD layer.

Wraps ``database.repository`` with business rules, input validation and
convenience queries so callers don't reach into SQLite directly.
"""

from __future__ import annotations

from typing import Optional

from database import repository as repo
from database.db_setup import get_connection


class ExerciseManager:
    """Higher-level exercise library management."""

    def __init__(self, connection=None) -> None:
        self._owns_connection = connection is None
        self.conn = connection or get_connection()

    def close(self) -> None:
        if self._owns_connection:
            self.conn.close()

    def __enter__(self) -> "ExerciseManager":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # ------------------------------------------------------------------ CRUD

    def add_exercise(
        self,
        name: str,
        primary_muscle_group: str,
        equipment: str,
        secondary_muscle_group: Optional[str] = None,
        is_custom: int = 0,
        created_by_user_id: Optional[int] = None,
    ) -> int:
        """Add an exercise to the library. Returns the new exercise id."""
        return repo.create_exercise(
            conn=self.conn,
            name=name,
            primary_muscle_group=primary_muscle_group,
            secondary_muscle_group=secondary_muscle_group,
            equipment=equipment,
            is_custom=is_custom,
            created_by_user_id=created_by_user_id,
        )

    def get_exercise(self, exercise_id: int) -> Optional[dict]:
        row = repo.get_exercise(self.conn, exercise_id)
        return dict(row) if row else None

    def get_exercise_by_name(self, name: str) -> Optional[dict]:
        row = repo.get_exercise_by_name(self.conn, name)
        return dict(row) if row else None

    def list_exercises(
        self,
        primary_muscle_group: Optional[str] = None,
        equipment: Optional[str] = None,
        custom_only: bool = False,
    ) -> list[dict]:
        rows = repo.list_exercises(
            self.conn,
            primary_muscle_group=primary_muscle_group,
            equipment=equipment,
            custom_only=custom_only,
        )
        return [dict(row) for row in rows]

    def update_exercise(self, exercise_id: int, **fields) -> int:
        return repo.update_exercise(self.conn, exercise_id, **fields)

    def delete_exercise(self, exercise_id: int) -> int:
        return repo.delete_exercise(self.conn, exercise_id)

    # ------------------------------------------------------------------ queries

    def list_muscle_groups(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT primary_muscle_group FROM exercises ORDER BY primary_muscle_group"
        ).fetchall()
        return [row["primary_muscle_group"] for row in rows]

    def list_equipment(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT equipment FROM exercises ORDER BY equipment"
        ).fetchall()
        return [row["equipment"] for row in rows]

    def search(self, query: str) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT * FROM exercises
            WHERE name LIKE ? OR primary_muscle_group LIKE ? OR equipment LIKE ?
            ORDER BY primary_muscle_group, name
            """,
            (f"%{query}%", f"%{query}%", f"%{query}%"),
        ).fetchall()
        return [dict(row) for row in rows]
