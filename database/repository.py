"""CRUD layer for the fitness database.

All functions are thin wrappers around sqlite3. They expect a connection with
``row_factory = sqlite3.Row`` and ``PRAGMA foreign_keys = ON`` already set
(see :func:`database.db_setup.get_connection`).

Return types:

* ``sqlite3.Row`` (dict-like) for single records
* ``list[sqlite3.Row]`` for collections
* ``int`` for the new primary key on inserts
* ``None`` when nothing matches

Helper functions at the bottom expose joined views used by later phases
(workout history, personal records, program listing).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import sqlite3

from database.db_setup import get_connection

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


def create_user(
    conn: sqlite3.Connection,
    name: str,
    age: Optional[int] = None,
    height_cm: Optional[float] = None,
    weight_kg: Optional[float] = None,
    goal: Optional[str] = None,
) -> int:
    """Insert a user profile and return the new user id."""
    cursor = conn.execute(
        """
        INSERT INTO users (name, age, height_cm, weight_kg, goal)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, age, height_cm, weight_kg, goal),
    )
    conn.commit()
    return int(cursor.lastrowid)


def get_user(conn: sqlite3.Connection, user_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_user_by_name(conn: sqlite3.Connection, name: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM users WHERE name = ?", (name,)
    ).fetchone()


def list_users(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM users ORDER BY name").fetchall()


def update_user(
    conn: sqlite3.Connection,
    user_id: int,
    **fields,
) -> int:
    """Update the given columns for a user. Returns rows affected."""
    if not fields:
        return 0
    set_clause = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [user_id]
    cursor = conn.execute(
        f"UPDATE users SET {set_clause}, updated_at = datetime('now') WHERE id = ?",
        values,
    )
    conn.commit()
    return cursor.rowcount


def delete_user(conn: sqlite3.Connection, user_id: int) -> int:
    """Delete a user. Sessions, sets, recovery logs and programs cascade."""
    cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    return cursor.rowcount


# ---------------------------------------------------------------------------
# Exercises
# ---------------------------------------------------------------------------


def create_exercise(
    conn: sqlite3.Connection,
    name: str,
    primary_muscle_group: str,
    equipment: str,
    secondary_muscle_group: Optional[str] = None,
    is_custom: int = 0,
    created_by_user_id: Optional[int] = None,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO exercises
            (name, primary_muscle_group, secondary_muscle_group, equipment, is_custom, created_by_user_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, primary_muscle_group, secondary_muscle_group, equipment, is_custom, created_by_user_id),
    )
    conn.commit()
    return int(cursor.lastrowid)


def get_exercise(conn: sqlite3.Connection, exercise_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM exercises WHERE id = ?", (exercise_id,)
    ).fetchone()


def get_exercise_by_name(conn: sqlite3.Connection, name: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM exercises WHERE name = ?", (name,)
    ).fetchone()


def list_exercises(
    conn: sqlite3.Connection,
    primary_muscle_group: Optional[str] = None,
    equipment: Optional[str] = None,
    custom_only: bool = False,
    include_archived: bool = False,
) -> list[sqlite3.Row]:
    query = "SELECT * FROM exercises WHERE 1 = 1"
    params: list = []
    if not include_archived:
        # ``is_active`` may not exist on databases created before the archiving
        # migration; guard for that so older installs keep working.
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(exercises)")}
        if "is_active" in cols:
            query += " AND is_active = 1"
    if primary_muscle_group:
        query += " AND primary_muscle_group = ?"
        params.append(primary_muscle_group)
    if equipment:
        query += " AND equipment = ?"
        params.append(equipment)
    if custom_only:
        query += " AND is_custom = 1"
    query += " ORDER BY primary_muscle_group, name"
    return conn.execute(query, params).fetchall()


def list_exercises_including_archived(
    conn: sqlite3.Connection,
    primary_muscle_group: Optional[str] = None,
    equipment: Optional[str] = None,
) -> list[sqlite3.Row]:
    """Return all exercises, including archived ones, for history views."""
    return list_exercises(
        conn,
        primary_muscle_group=primary_muscle_group,
        equipment=equipment,
        include_archived=True,
    )


def update_exercise(conn: sqlite3.Connection, exercise_id: int, **fields) -> int:
    if not fields:
        return 0
    set_clause = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [exercise_id]
    cursor = conn.execute(
        f"UPDATE exercises SET {set_clause} WHERE id = ?", values
    )
    conn.commit()
    return cursor.rowcount


def set_exercise_active(conn: sqlite3.Connection, exercise_id: int, active: bool) -> int:
    """Archive (active=False) or restore (active=True) an exercise.

    Returns the number of rows updated.
    """
    return update_exercise(conn, exercise_id, is_active=1 if active else 0)


def delete_exercise(conn: sqlite3.Connection, exercise_id: int) -> int:
    """Delete an exercise.

    Refuses to delete an exercise that has historical workout sets, because
    ``workout_sets.exercise_id`` references it (FK ``ON DELETE RESTRICT``).
    Callers should use :func:`set_exercise_active` to archive instead when
    history exists. Returns rows affected (0 when refused).
    """
    in_use = conn.execute(
        """
        SELECT COUNT(*) AS c FROM workout_sets WHERE exercise_id = ?
        """,
        (exercise_id,),
    ).fetchone()["c"]
    if in_use:
        return 0
    cursor = conn.execute("DELETE FROM exercises WHERE id = ?", (exercise_id,))
    conn.commit()
    return cursor.rowcount


# ---------------------------------------------------------------------------
# Workout sessions and sets
# ---------------------------------------------------------------------------


def create_session(
    conn: sqlite3.Connection,
    user_id: int,
    session_date: str,
    duration_min: Optional[int] = None,
    notes: Optional[str] = None,
) -> int:
    """Create a workout session for a user on a given date (YYYY-MM-DD).

    Raises sqlite3.IntegrityError if the user already has a session that day.
    """
    cursor = conn.execute(
        """
        INSERT INTO workout_sessions (user_id, session_date, duration_min, notes)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, session_date, duration_min, notes),
    )
    conn.commit()
    return int(cursor.lastrowid)


def get_session(conn: sqlite3.Connection, session_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM workout_sessions WHERE id = ?", (session_id,)
    ).fetchone()


def list_sessions_by_user(
    conn: sqlite3.Connection,
    user_id: int,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[sqlite3.Row]:
    query = "SELECT * FROM workout_sessions WHERE user_id = ? ORDER BY session_date DESC"
    params: list = [user_id]
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
    if offset is not None:
        query += " OFFSET ?"
        params.append(offset)
    return conn.execute(query, params).fetchall()


def update_session(
    conn: sqlite3.Connection,
    session_id: int,
    **fields,
) -> int:
    if not fields:
        return 0
    set_clause = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [session_id]
    cursor = conn.execute(
        f"UPDATE workout_sessions SET {set_clause} WHERE id = ?", values
    )
    conn.commit()
    return cursor.rowcount


def delete_session(conn: sqlite3.Connection, session_id: int) -> int:
    cursor = conn.execute("DELETE FROM workout_sessions WHERE id = ?", (session_id,))
    conn.commit()
    return cursor.rowcount


def add_set(
    conn: sqlite3.Connection,
    session_id: int,
    exercise_id: int,
    set_number: int,
    reps: int,
    weight_kg: float,
    rpe: Optional[float] = None,
) -> int:
    """Add one set record to a session."""
    cursor = conn.execute(
        """
        INSERT INTO workout_sets (session_id, exercise_id, set_number, reps, weight_kg, rpe)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (session_id, exercise_id, set_number, reps, weight_kg, rpe),
    )
    conn.commit()
    return int(cursor.lastrowid)


def get_sets_for_session(conn: sqlite3.Connection, session_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT ws.*, e.name AS exercise_name, e.primary_muscle_group
        FROM workout_sets ws
        JOIN exercises e ON ws.exercise_id = e.id
        WHERE ws.session_id = ?
        ORDER BY ws.set_number
        """,
        (session_id,),
    ).fetchall()


def update_set(conn: sqlite3.Connection, set_id: int, **fields) -> int:
    if not fields:
        return 0
    set_clause = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [set_id]
    cursor = conn.execute(
        f"UPDATE workout_sets SET {set_clause} WHERE id = ?", values
    )
    conn.commit()
    return cursor.rowcount


def delete_set(conn: sqlite3.Connection, set_id: int) -> int:
    cursor = conn.execute("DELETE FROM workout_sets WHERE id = ?", (set_id,))
    conn.commit()
    return cursor.rowcount


# ---------------------------------------------------------------------------
# Recovery logs
# ---------------------------------------------------------------------------


def log_recovery(
    conn: sqlite3.Connection,
    user_id: int,
    log_date: str,
    sleep_hours: Optional[float] = None,
    body_weight_kg: Optional[float] = None,
    soreness: Optional[int] = None,
    energy: Optional[int] = None,
) -> int:
    """Insert or update a recovery record for a user on a given date (YYYY-MM-DD)."""
    existing = conn.execute(
        "SELECT id FROM recovery_logs WHERE user_id = ? AND log_date = ?",
        (user_id, log_date),
    ).fetchone()

    if existing:
        cursor = conn.execute(
            """
            UPDATE recovery_logs
            SET sleep_hours = COALESCE(?, sleep_hours),
                body_weight_kg = COALESCE(?, body_weight_kg),
                soreness = COALESCE(?, soreness),
                energy = COALESCE(?, energy)
            WHERE id = ?
            """,
            (sleep_hours, body_weight_kg, soreness, energy, existing["id"]),
        )
        conn.commit()
        return int(existing["id"])

    cursor = conn.execute(
        """
        INSERT INTO recovery_logs (user_id, log_date, sleep_hours, body_weight_kg, soreness, energy)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, log_date, sleep_hours, body_weight_kg, soreness, energy),
    )
    conn.commit()
    return int(cursor.lastrowid)


def get_recovery(
    conn: sqlite3.Connection,
    user_id: int,
    log_date: str,
) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM recovery_logs WHERE user_id = ? AND log_date = ?",
        (user_id, log_date),
    ).fetchone()


def list_recovery_by_user(
    conn: sqlite3.Connection,
    user_id: int,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[sqlite3.Row]:
    query = "SELECT * FROM recovery_logs WHERE user_id = ? ORDER BY log_date DESC"
    params: list = [user_id]
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
    if offset is not None:
        query += " OFFSET ?"
        params.append(offset)
    return conn.execute(query, params).fetchall()


def update_recovery(conn: sqlite3.Connection, recovery_id: int, **fields) -> int:
    if not fields:
        return 0
    set_clause = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [recovery_id]
    cursor = conn.execute(
        f"UPDATE recovery_logs SET {set_clause} WHERE id = ?", values
    )
    conn.commit()
    return cursor.rowcount


def delete_recovery(conn: sqlite3.Connection, recovery_id: int) -> int:
    cursor = conn.execute("DELETE FROM recovery_logs WHERE id = ?", (recovery_id,))
    conn.commit()
    return cursor.rowcount


# ---------------------------------------------------------------------------
# Training programs
# ---------------------------------------------------------------------------


def create_program(
    conn: sqlite3.Connection,
    user_id: int,
    name: str,
    split_type: str,
    is_active: int = 0,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO training_programs (user_id, name, split_type, is_active)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, name, split_type, is_active),
    )
    conn.commit()
    return int(cursor.lastrowid)


def get_program(conn: sqlite3.Connection, program_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM training_programs WHERE id = ?", (program_id,)
    ).fetchone()


def list_programs_by_user(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM training_programs WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()


def delete_program(conn: sqlite3.Connection, program_id: int) -> int:
    cursor = conn.execute("DELETE FROM training_programs WHERE id = ?", (program_id,))
    conn.commit()
    return cursor.rowcount


def create_program_day(
    conn: sqlite3.Connection,
    program_id: int,
    day_name: str,
    day_order: int,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO program_days (program_id, day_name, day_order)
        VALUES (?, ?, ?)
        """,
        (program_id, day_name, day_order),
    )
    conn.commit()
    return int(cursor.lastrowid)


def add_program_exercise(
    conn: sqlite3.Connection,
    program_day_id: int,
    exercise_id: int,
    target_sets: Optional[int] = None,
    target_reps: Optional[int] = None,
    target_weight_kg: Optional[float] = None,
    notes: Optional[str] = None,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO program_exercises
            (program_day_id, exercise_id, target_sets, target_reps, target_weight_kg, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (program_day_id, exercise_id, target_sets, target_reps, target_weight_kg, notes),
    )
    conn.commit()
    return int(cursor.lastrowid)


def list_program_days_with_exercises(
    conn: sqlite3.Connection,
    program_id: int,
) -> list[sqlite3.Row]:
    """Return program days with their assigned exercises joined."""
    return conn.execute(
        """
        SELECT pd.id AS day_id, pd.day_name, pd.day_order,
               e.id AS exercise_id, e.name AS exercise_name,
               e.primary_muscle_group, e.equipment,
               pe.target_sets, pe.target_reps, pe.target_weight_kg, pe.notes
        FROM program_days pd
        LEFT JOIN program_exercises pe ON pe.program_day_id = pd.id
        LEFT JOIN exercises e ON pe.exercise_id = e.id
        WHERE pd.program_id = ?
        ORDER BY pd.day_order, pd.id, pe.id
        """,
        (program_id,),
    ).fetchall()


# ---------------------------------------------------------------------------
# Joined views used by later phases
# ---------------------------------------------------------------------------


def workout_history(
    conn: sqlite3.Connection,
    user_id: int,
) -> list[sqlite3.Row]:
    """Every set for a user, joined to session date, duration and exercise."""
    return conn.execute(
        """
        SELECT ws.id, ws.session_id, s.session_date, s.duration_min, s.notes,
               ws.exercise_id, e.name AS exercise_name,
               e.primary_muscle_group, e.equipment,
               ws.set_number, ws.reps, ws.weight_kg, ws.rpe
        FROM workout_sets ws
        JOIN workout_sessions s ON ws.session_id = s.id
        JOIN exercises e ON ws.exercise_id = e.id
        WHERE s.user_id = ?
        ORDER BY s.session_date DESC, ws.set_number
        """,
        (user_id,),
    ).fetchall()


def personal_records(
    conn: sqlite3.Connection,
    user_id: int,
    exercise_id: int,
) -> list[dict]:
    """Best single-set metrics per exercise for a user.

    Every reported value comes from an actually performed set, so the UI never
    displays a weight/repetition combination that was never performed.

    Returns a list with a single dict (empty when the exercise has no sets)
    containing:

    * ``max_weight_kg`` / ``max_weight_reps`` - heaviest set actually lifted
    * ``max_reps`` / ``max_reps_weight`` - most reps actually performed
    * ``max_volume_kg`` / ``max_volume_reps`` / ``max_volume_weight`` - highest
      single-set volume (reps × weight) actually performed
    * ``best_e1rm_kg`` / ``best_e1rm_weight`` / ``best_e1rm_reps`` - highest
      estimated one-rep max (Epley) across all performed sets
    * ``set_count`` - number of sets on record
    """
    rows = conn.execute(
        """
        SELECT ws.set_number, ws.reps, ws.weight_kg, ws.rpe,
               e.name AS exercise_name
        FROM workout_sets ws
        JOIN exercises e ON ws.exercise_id = e.id
        JOIN workout_sessions s ON ws.session_id = s.id
        WHERE s.user_id = ? AND ws.exercise_id = ?
        ORDER BY s.session_date DESC, ws.set_number
        """,
        (user_id, exercise_id),
    ).fetchall()

    if not rows:
        return []

    sets = [dict(r) for r in rows]
    exercise_name = sets[0]["exercise_name"]

    def e1rm(weight_kg: float, reps: int) -> float:
        return float(weight_kg) * (1 + float(reps) / 30.0)

    # Heaviest set actually performed (tiebreak: more reps, then later set).
    max_weight_set = max(
        sets, key=lambda s: (s["weight_kg"], s["reps"], s["set_number"])
    )
    # Most reps actually performed (tiebreak: heavier weight, then later set).
    max_reps_set = max(
        sets, key=lambda s: (s["reps"], s["weight_kg"], s["set_number"])
    )
    # Highest single-set volume actually performed.
    max_volume_set = max(
        sets, key=lambda s: (s["reps"] * s["weight_kg"], s["weight_kg"], s["set_number"])
    )
    # Highest estimated 1RM across performed sets.
    best_e1rm_set = max(sets, key=lambda s: e1rm(s["weight_kg"], s["reps"]))

    return [
        {
            "exercise_name": exercise_name,
            "max_weight_kg": float(max_weight_set["weight_kg"]),
            "max_weight_reps": int(max_weight_set["reps"]),
            "max_reps": int(max_reps_set["reps"]),
            "max_reps_weight": float(max_reps_set["weight_kg"]),
            "max_volume_kg": float(max_volume_set["reps"] * max_volume_set["weight_kg"]),
            "max_volume_reps": int(max_volume_set["reps"]),
            "max_volume_weight": float(max_volume_set["weight_kg"]),
            "best_e1rm_kg": float(e1rm(best_e1rm_set["weight_kg"], best_e1rm_set["reps"])),
            "best_e1rm_weight": float(best_e1rm_set["weight_kg"]),
            "best_e1rm_reps": int(best_e1rm_set["reps"]),
            "set_count": len(sets),
        }
    ]
