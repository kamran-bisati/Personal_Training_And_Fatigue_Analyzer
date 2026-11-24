"""History page: previous sessions and personal records."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from database import repository as repo
from streamlit_app.utils import load_workout_df


def render(conn, user_id: int) -> None:
    st.title("History — Workout History & Personal Records")

    workout_df = load_workout_df(conn, user_id)

    if workout_df.empty:
        st.info("No workout history yet. Go to Train to log your first workout.")
        return

    # ---------- Session list ----------
    st.subheader("Past Sessions")
    sessions = repo.list_sessions_by_user(conn, user_id)
    for s in sessions:
        sets = repo.get_sets_for_session(conn, s["id"])
        total_vol = sum(float(se["reps"]) * float(se["weight_kg"]) for se in sets)
        with st.expander(f"{s['session_date']} — {len(sets)} set(s), {total_vol:,.0f} kg"):
            for se in sets:
                st.write(
                    f"• {se['exercise_name']}: {se['reps']} reps × {se['weight_kg']} kg, "
                    f"RPE {se['rpe']} (Set {se['set_number']})"
                )
            if st.button("Delete Session", key=f"del_sess_{s['id']}"):
                try:
                    # Delete sets first (cascade should handle, but explicit)
                    for se in sets:
                        repo.delete_set(conn, se["id"])
                    repo.delete_session(conn, s["id"])
                    st.success("Session deleted")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Failed to delete: {exc}")

    st.divider()

    # ---------- Personal Records ----------
    st.subheader("Personal Records (by Exercise)")
    exercises = repo.list_exercises(conn, include_archived=True)
    if not exercises:
        st.caption("No exercises in library.")
        return

    for ex in exercises:
        prs = repo.personal_records(conn, user_id, ex["id"])
        if prs:
            pr = prs[0]
            st.write(
                f"**{pr['exercise_name']}**: "
                f"heaviest {pr['max_weight_kg']:.1f} kg × {pr['max_weight_reps']} reps | "
                f"most reps {pr['max_reps']} × {pr['max_reps_weight']:.1f} kg | "
                f"best single-set volume {pr['max_volume_kg']:,.0f} kg "
                f"({pr['max_volume_weight']:.1f} × {pr['max_volume_reps']}) | "
                f"est. 1RM {pr['best_e1rm_kg']:.1f} kg "
                f"({pr['best_e1rm_weight']:.1f} × {pr['best_e1rm_reps']})"
            )
        else:
            st.write(f"**{ex['name']}**: No records yet")

    st.divider()

    # ---------- Full data table ----------
    st.subheader("All Set Records (Data View)")
    st.dataframe(
        workout_df.sort_values("date", ascending=False),
        hide_index=True,
    )
