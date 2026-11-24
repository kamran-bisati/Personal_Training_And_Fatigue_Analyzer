"""Exercises page: exercise library management."""

from __future__ import annotations

import streamlit as st

from database import repository as repo


def _exercise_in_use(conn, exercise_id: int) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM workout_sets WHERE exercise_id = ?",
        (exercise_id,),
    ).fetchone()
    return int(row["c"]) > 0


def render(conn, user_id: int) -> None:
    st.title("Exercises — Exercise Library")

    tab_browse, tab_add = st.tabs(["Browse Library", "Add Exercise"])

    # ---------- Tab: Browse ----------
    with tab_browse:
        st.subheader("All Exercises")

        # Build filter options dynamically
        all_ex = repo.list_exercises(conn, include_archived=True)
        muscle_groups = sorted({e["primary_muscle_group"] for e in all_ex if e["primary_muscle_group"]})
        equipment_types = sorted({e["equipment"] for e in all_ex if e["equipment"]})

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            m_filter = st.selectbox("Muscle Group", ["All"] + muscle_groups)
        with col_f2:
            e_filter = st.selectbox("Equipment", ["All"] + equipment_types)

        filtered = all_ex
        if m_filter != "All":
            filtered = [e for e in filtered if e["primary_muscle_group"] == m_filter]
        if e_filter != "All":
            filtered = [e for e in filtered if e["equipment"] == e_filter]

        if not filtered:
            st.caption("No exercises match the filters.")
        else:
            for e in filtered:
                in_use = _exercise_in_use(conn, e["id"])
                with st.expander(f"{e['name']}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.write(f"Primary Muscle: {e['primary_muscle_group']}")
                        st.write(f"Equipment: {e['equipment']}")
                    with c2:
                        st.write(f"Secondary Muscle: {e['secondary_muscle_group'] or '—'}")
                        st.write(f"Custom: {'Yes' if e['is_custom'] else 'No'}")
                        st.write(f"Status: {'Active' if e['is_active'] else 'Archived'}")
                    with c3:
                        if in_use:
                            # Exercise has history: archive instead of delete so
                            # historical workout sets are preserved.
                            if e["is_active"]:
                                if st.button("Archive", key=f"archive_ex_{e['id']}"):
                                    try:
                                        repo.set_exercise_active(conn, e["id"], False)
                                        st.success("Exercise archived. History preserved.")
                                        st.rerun()
                                    except Exception as exc:
                                        st.error(f"Failed to archive: {exc}")
                            else:
                                if st.button("Restore", key=f"restore_ex_{e['id']}"):
                                    try:
                                        repo.set_exercise_active(conn, e["id"], True)
                                        st.success("Exercise restored.")
                                        st.rerun()
                                    except Exception as exc:
                                        st.error(f"Failed to restore: {exc}")
                        else:
                            # No history: safe to delete permanently.
                            if st.button("Delete", key=f"del_ex_{e['id']}"):
                                try:
                                    affected = repo.delete_exercise(conn, e["id"])
                                    if affected:
                                        st.success("Deleted")
                                        st.rerun()
                                    else:
                                        st.error("Cannot delete: exercise has historical records.")
                                except Exception as exc:
                                    st.error(f"Cannot delete: {exc}")
                    st.divider()

    # ---------- Tab: Add ----------
    with tab_add:
        st.subheader("Add New Exercise")
        with st.form("add_exercise_form"):
            ex_name = st.text_input("Exercise Name")
            primary_muscle = st.text_input("Primary Muscle Group (e.g. Chest)")
            secondary_muscle = st.text_input("Secondary Muscle Group (optional)")
            equipment = st.text_input("Equipment (e.g. Barbell, Dumbbell, Cable, Machine, Bodyweight)")
            is_custom = st.checkbox("Custom exercise", value=True)
            submitted = st.form_submit_button("Add Exercise")
        if submitted:
            if not ex_name.strip() or not primary_muscle.strip() or not equipment.strip():
                st.error("Name, primary muscle group, and equipment are required.")
            else:
                # Prevent duplicate exercise names.
                if repo.get_exercise_by_name(conn, ex_name.strip()) is not None:
                    st.error(f"An exercise named '{ex_name.strip()}' already exists.")
                else:
                    try:
                        eid = repo.create_exercise(
                            conn=conn,
                            name=ex_name.strip(),
                            primary_muscle_group=primary_muscle.strip(),
                            secondary_muscle_group=secondary_muscle.strip() or None,
                            equipment=equipment.strip(),
                            is_custom=1 if is_custom else 0,
                            created_by_user_id=user_id,
                        )
                        st.success(f"Exercise added! ID: {eid}")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Failed to add exercise: {exc}")
