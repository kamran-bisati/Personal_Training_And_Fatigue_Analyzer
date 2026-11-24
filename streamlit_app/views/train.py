"""Train page: daily workout input form."""

from __future__ import annotations

from datetime import date
import streamlit as st

from database import repository as repo
from src.management.workout_manager import WorkoutManager


def _next_set_number(conn, session_id, exercise_id, pending_sets) -> int:
    """Suggest the next set number for an exercise in a session.

    Considers both already-saved sets in the database and sets currently in
    the pending cart, so the same set number is never suggested twice.
    """
    manager = WorkoutManager(connection=conn)
    try:
        next_num = manager.next_set_number(session_id, exercise_id)
    finally:
        manager.close()
    used = {int(s["set_number"]) for s in pending_sets if s["exercise_id"] == exercise_id}
    while next_num in used:
        next_num += 1
    return next_num


def render(conn, user_id: int) -> None:
    st.title("Train — Log Workout")

    # ---------- Session info ----------
    st.subheader("Session Details")
    col1, col2 = st.columns(2)
    with col1:
        session_date = st.date_input("Date", value=date.today())
    with col2:
        duration_min = st.number_input("Duration (min)", min_value=1, max_value=300, value=60, step=5)
    notes = st.text_input("Notes (optional)")

    session_date_str = session_date.isoformat()

    # Check if a session already exists for this date
    existing = repo.list_sessions_by_user(conn, user_id)
    existing_session = None
    for s in existing:
        if s["session_date"] == session_date_str:
            existing_session = s
            break

    if existing_session:
        st.info(f"A session already exists for {session_date_str}. You can add more sets to it.")
        session_id = existing_session["id"]
    else:
        session_id = None

    # ---------- Exercise library ----------
    st.subheader("Exercises")
    exercises = repo.list_exercises(conn)
    if not exercises:
        st.warning("No exercises in the library. Add some in the Exercises page first.")
        return

    # Display names, but keep database IDs as the underlying values so
    # duplicate exercise names cannot collide.
    exercise_options = {f"{e['name']} (ID {e['id']})": e["id"] for e in exercises}
    exercise_by_id = {e["id"]: e for e in exercises}

    # ---------- Add set form ----------
    st.subheader("Add Set")
    with st.form("add_set_form", clear_on_submit=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            ex_label = st.selectbox("Exercise", list(exercise_options.keys()))
        with c2:
            # Suggest the next set number for this exercise/session.
            ex_id = exercise_options[ex_label]
            suggested = _next_set_number(conn, session_id, ex_id, st.session_state.pending_sets)
            set_number = st.number_input("Set #", min_value=1, value=suggested, step=1)
        with c3:
            reps = st.number_input("Reps", min_value=1, max_value=100, value=8, step=1)
        with c4:
            weight_kg = st.number_input("Weight (kg)", min_value=0.0, max_value=500.0, value=0.0, step=2.5)
        with c5:
            rpe = st.number_input("RPE (1-10)", min_value=1.0, max_value=10.0, value=8.0, step=0.5)
        submitted = st.form_submit_button("Add Set to Cart")

    if submitted:
        ex_id = exercise_options[ex_label]
        new_set = {
            "exercise_id": ex_id,
            "exercise_name": exercise_by_id[ex_id]["name"],
            "set_number": int(set_number),
            "reps": int(reps),
            "weight_kg": float(weight_kg),
            "rpe": float(rpe),
        }
        # Prevent accidental duplicate set numbers for the same exercise.
        duplicate = any(
            s["exercise_id"] == ex_id and int(s["set_number"]) == int(set_number)
            for s in st.session_state.pending_sets
        )
        if duplicate:
            st.error(
                f"Set #{int(set_number)} for {exercise_by_id[ex_id]['name']} is already in the cart. "
                "Change the set number or remove the existing set first."
            )
        else:
            st.session_state.pending_sets.append(new_set)
            st.success(
                f"Added: {exercise_by_id[ex_id]['name']} — {reps} reps × {weight_kg} kg @ RPE {rpe}"
            )

    # ---------- Pending sets ----------
    if st.session_state.pending_sets:
        st.subheader("Sets to Save")
        total_volume = 0.0
        for i, s in enumerate(st.session_state.pending_sets):
            vol = s["reps"] * s["weight_kg"]
            total_volume += vol
            cols = st.columns([3, 1, 1, 1, 1, 1])
            with cols[0]:
                st.write(f"{s['exercise_name']}")
            with cols[1]:
                st.write(f"Set {s['set_number']}")
            with cols[2]:
                st.write(f"{s['reps']} reps")
            with cols[3]:
                st.write(f"{s['weight_kg']} kg")
            with cols[4]:
                st.write(f"RPE {s['rpe']}")
            with cols[5]:
                if st.button("✕", key=f"remove_set_{i}"):
                    st.session_state.pending_sets.pop(i)
                    st.rerun()
        st.write(f"**Pending volume: {total_volume:,.0f} kg**")

        col_save, col_clear = st.columns(2)
        with col_save:
            saving = st.session_state.get("workout_saving", False)
            if st.button(
                "Save Workout",
                type="primary",
                width="stretch",
                disabled=saving,
            ):
                # Guard against double submission.
                st.session_state.workout_saving = True
                try:
                    wm = WorkoutManager(connection=conn)
                    try:
                        if session_id is None:
                            session_id = wm.create_session(
                                user_id=user_id,
                                session_date=session_date_str,
                                duration_min=int(duration_min),
                                notes=notes or None,
                            )
                        for s in st.session_state.pending_sets:
                            wm.add_set(
                                session_id=session_id,
                                exercise_id=s["exercise_id"],
                                set_number=s["set_number"],
                                reps=s["reps"],
                                weight_kg=s["weight_kg"],
                                rpe=s["rpe"],
                            )
                        st.session_state.pending_sets = []
                        st.session_state.pending_sets_user_id = user_id
                        st.success(f"Workout saved! Session ID: {session_id}")
                        st.rerun()
                    finally:
                        wm.close()
                except Exception as exc:
                    st.error(f"Failed to save workout: {exc}")
                finally:
                    st.session_state.workout_saving = False
        with col_clear:
            if st.button("Clear All", width="stretch"):
                st.session_state.pending_sets = []
                st.rerun()
    else:
        st.caption("Add sets using the form above, then click Save Workout.")
