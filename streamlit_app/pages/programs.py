"""Programs page: workout splits and schedules."""

from __future__ import annotations

import streamlit as st

from database import repository as repo
from src.management.program_manager import ProgramManager


def render(conn, user_id: int) -> None:
    st.title("Programs — Training Splits & Schedules")

    tab_list, tab_create, tab_template = st.tabs(
        ["My Programs", "Create Custom Program", "Create from Template"]
    )

    # ---------- Tab: My Programs ----------
    with tab_list:
        st.subheader("Your Programs")
        programs = repo.list_programs_by_user(conn, user_id)
        if not programs:
            st.caption("No programs yet. Create one below.")
        else:
            for p in programs:
                active = " (ACTIVE)" if p["is_active"] else ""
                with st.expander(f"{p['name']} — {p['split_type']}{active}"):
                    st.write(f"Split type: {p['split_type']}")
                    st.write(f"Created: {p['created_at']}")
                    structure = repo.list_program_days_with_exercises(conn, p["id"])
                    if structure:
                        days = {}
                        for row in structure:
                            dn = row["day_name"]
                            if dn not in days:
                                days[dn] = []
                            if row["exercise_name"]:
                                days[dn].append(
                                    f"• {row['exercise_name']} ({row['primary_muscle_group']}) "
                                    f"— {row['target_sets'] or '?'}×{row['target_reps'] or '?'}"
                                )
                        for day_name, exs in days.items():
                            st.write(f"**{day_name}:**")
                            for e in exs:
                                st.write(e)
                    col_act, col_del = st.columns(2)
                    with col_act:
                        if not p["is_active"]:
                            if st.button("Set Active", key=f"activate_{p['id']}"):
                                pm = ProgramManager(connection=conn)
                                try:
                                    pm.set_active_program(user_id, p["id"])
                                    st.success(f"Activated: {p['name']}")
                                    st.rerun()
                                finally:
                                    pm.close()
                    with col_del:
                        if st.button("Delete", key=f"delete_prog_{p['id']}"):
                            pm = ProgramManager(connection=conn)
                            try:
                                pm.delete_program(p["id"])
                                st.success("Deleted")
                                st.rerun()
                            finally:
                                pm.close()

    # ---------- Tab: Create Custom Program ----------
    with tab_create:
        st.subheader("Create Custom Program")
        with st.form("create_program_form"):
            prog_name = st.text_input("Program Name")
            split_type = st.selectbox(
                "Split Type", ["PPL", "Upper/Lower", "Full Body", "Custom"]
            )
            is_active = st.checkbox("Set as active program")
            submitted = st.form_submit_button("Create Program")
        if submitted and prog_name.strip():
            try:
                pm = ProgramManager(connection=conn)
                try:
                    pid = pm.create_program(
                        user_id=user_id,
                        name=prog_name.strip(),
                        split_type=split_type,
                        is_active=1 if is_active else 0,
                    )
                    st.success(f"Program created! ID: {pid}")
                    st.info("Add days and exercises in the 'My Programs' tab, or create days here.")
                    # Day adder
                    st.subheader("Add Training Day")
                    day_name = st.text_input("Day Name (e.g. Push Day)", key="day_name_new")
                    day_order = st.number_input("Day Order", min_value=1, value=1, step=1, key="day_order_new")
                    if st.button("Add Day", key="add_day_btn"):
                        if day_name.strip():
                            pm.add_day(pid, day_name.strip(), int(day_order))
                            st.success(f"Added day: {day_name.strip()}")
                            st.rerun()
                finally:
                    pm.close()
            except Exception as exc:
                st.error(f"Failed to create program: {exc}")

    # ---------- Tab: Create from Template ----------
    with tab_template:
        st.subheader("Create from Preset Template")
        st.write("Choose a built-in split. Exercises are matched to the library by name.")

        template = st.selectbox("Template", ["PPL", "Upper/Lower"])
        prog_name = st.text_input("Program Name", value=f"{template} Program")

        template_details = {
            "PPL": "3 days: Push, Pull, Legs",
            "Upper/Lower": "4 days: Upper A, Lower A, Upper B, Lower B",
        }
        st.caption(template_details[template])

        if st.button("Create Program from Template", type="primary", width="stretch"):
            if not prog_name.strip():
                st.error("Please enter a program name.")
            else:
                try:
                    pm = ProgramManager(connection=conn)
                    try:
                        pid = pm.create_from_template(
                            user_id=user_id,
                            name=prog_name.strip(),
                            split_type=template,
                            template=template,
                        )
                        st.success(f"Created '{prog_name.strip()}' from {template} template! ID: {pid}")
                        structure = pm.get_program_structure(pid)
                        st.write(f"{len(structure)} exercise assignments across the program days.")
                        for row in structure:
                            st.write(
                                f"• {row['day_name']}: {row['exercise_name']} — "
                                f"{row['target_sets'] or '?'}×{row['target_reps'] or '?'}"
                            )
                    finally:
                        pm.close()
                    st.rerun()
                except Exception as exc:
                    st.error(f"Failed to create program: {exc}")
