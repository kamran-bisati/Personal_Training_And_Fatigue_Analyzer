"""Exercises page: exercise library management."""

from __future__ import annotations

import streamlit as st

from database import repository as repo


def render(conn, user_id: int) -> None:
    st.title("Exercises — Exercise Library")

    tab_browse, tab_add = st.tabs(["Browse Library", "Add Exercise"])

    # ---------- Tab: Browse ----------
    with tab_browse:
        st.subheader("All Exercises")

        # Build filter options dynamically
        all_ex = repo.list_exercises(conn)
        muscle_groups = sorted({e["primary_muscle_group"] for e in all_ex if e["primary_muscle_group"]})
        equipment_types = sorted({e["equipment"] for e in all_ex if e["equipment"]})

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
                with st.expander(f"{e['name']}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.write(f"Primary Muscle: {e['primary_muscle_group']}")
                        st.write(f"Equipment: {e['equipment']}")
                    with c2:
                        st.write(f"Secondary Muscle: {e['secondary_muscle_group'] or '—'}")
                        st.write(f"Custom: {'Yes' if e['is_custom'] else 'No'}")
                    with c3:
                        if st.button("Delete", key=f"del_ex_{e['id']}"):
                            try:
                                repo.delete_exercise(conn, e["id"])
                                st.success("Deleted")
                                st.rerun()
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
