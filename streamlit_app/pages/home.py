"""Home page: daily summary and overview dashboard."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from database import repository as repo
from streamlit_app.utils import load_workout_df, load_recovery_df
from src.reporting.report_generator import daily_summary_report, weekly_report


def render(conn, user_id: int) -> None:
    st.title("Home — Daily Summary")

    workout_df = load_workout_df(conn, user_id)
    recovery_df = load_recovery_df(conn, user_id)

    # ---------- Headline metrics ----------
    col1, col2, col3, col4 = st.columns(4)

    total_sessions = int(workout_df["date"].nunique()) if not workout_df.empty else 0
    total_volume = float(workout_df["sets"].mul(workout_df["reps"]).mul(workout_df["weight_kg"]).sum()) if not workout_df.empty else 0.0

    latest_weight = None
    if not recovery_df.empty and "body_weight_kg" in recovery_df.columns:
        bw = recovery_df.dropna(subset=["body_weight_kg"])
        if not bw.empty:
            latest_weight = float(bw.sort_values("date")["body_weight_kg"].iloc[-1])

    avg_sleep = None
    if not recovery_df.empty and "sleep_hours" in recovery_df.columns:
        sleep = recovery_df.dropna(subset=["sleep_hours"])
        if not sleep.empty:
            avg_sleep = round(float(sleep["sleep_hours"].mean()), 1)

    with col1:
        st.metric("Total Sessions", total_sessions)
    with col2:
        st.metric("Total Volume (kg)", f"{total_volume:,.0f}")
    with col3:
        st.metric("Latest Body Weight (kg)", f"{latest_weight}" if latest_weight is not None else "—")
    with col4:
        st.metric("Avg Sleep (h)", f"{avg_sleep}" if avg_sleep is not None else "—")

    st.divider()

    # ---------- Daily summary (most recent day) ----------
    st.subheader("Most Recent Day")
    daily = daily_summary_report(workout_df, recovery_df)
    if "error" in daily:
        st.info(daily["error"])
    else:
        c1, c2 = st.columns(2)
        with c1:
            w = daily["workout"]
            st.write(f"**Date:** {daily['date']}")
            st.write(f"Sets: {w['n_sets']} | Exercises: {w['n_exercises']}")
            st.write(f"Volume: {w['total_volume_kg']:,.0f} kg")
            if w["avg_rpe"] is not None:
                st.write(f"Avg RPE: {w['avg_rpe']}")
        with c2:
            r = daily["recovery"]
            parts = []
            if r["sleep_hours"] is not None:
                parts.append(f"Sleep: {r['sleep_hours']} h")
            if r["soreness"] is not None:
                parts.append(f"Soreness: {r['soreness']}/10")
            if r["energy"] is not None:
                parts.append(f"Energy: {r['energy']}/10")
            if r["body_weight_kg"] is not None:
                parts.append(f"Weight: {r['body_weight_kg']} kg")
            st.write(" | ".join(parts) if parts else "No recovery data")
        st.caption(daily["interpretation"])

    st.divider()

    # ---------- Weekly report ----------
    st.subheader("This Week")
    weekly = weekly_report(workout_df, recovery_df)
    if "error" in weekly:
        st.info(weekly["error"])
    else:
        w = weekly["workout"]
        r = weekly["recovery"]
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Sessions", w["n_sessions"])
        with c2:
            st.metric("Volume (kg)", f"{w['total_volume_kg']:,.0f}")
        with c3:
            st.metric("Avg RPE", f"{w['avg_rpe']}" if w["avg_rpe"] is not None else "—")
        with c4:
            st.metric("Days Logged", r.get("n_days_logged", 0))
        st.caption(weekly["interpretation"])

    st.divider()

    # ---------- Recent activity ----------
    st.subheader("Recent Sessions")
    sessions = repo.list_sessions_by_user(conn, user_id, limit=5)
    if sessions:
        for s in sessions:
            sets = repo.get_sets_for_session(conn, s["id"])
            n_sets = len(sets)
            vol = sum(
                float(se["reps"]) * float(se["weight_kg"]) for se in sets
            )
            with st.expander(f"{s['session_date']} — {n_sets} set(s), {vol:,.0f} kg"):
                for se in sets:
                    st.write(
                        f"• {se['exercise_name']}: {se['reps']} reps × {se['weight_kg']} kg, RPE {se['rpe']}"
                    )
    else:
        st.caption("No sessions yet. Go to Train to log your first workout.")

    st.divider()
    st.subheader("Recent Recovery")
    recovery_rows = repo.list_recovery_by_user(conn, user_id, limit=5)
    if recovery_rows:
        for r in recovery_rows:
            st.write(
                f"• {r['log_date']}: sleep {r['sleep_hours']} h, "
                f"weight {r['body_weight_kg']} kg, soreness {r['soreness']}/10, "
                f"energy {r['energy']}/10"
            )
    else:
        st.caption("No recovery logs yet. Go to Recovery to log your first day.")
