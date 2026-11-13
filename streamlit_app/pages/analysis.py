"""Analysis page: charts, metrics, progression, detection alerts."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from database import repository as repo
from streamlit_app.utils import load_workout_df, load_recovery_df

from src.metrics.training_volume import bulk_training_volume
from src.metrics.estimated_1rm import bulk_estimated_1rm
from src.metrics.progression import bulk_strength_progression
from src.metrics.muscle_workload import bulk_muscle_workload
from src.metrics.average_rpe import bulk_average_rpe
from src.metrics.recovery_metrics import bulk_recovery_summary

from src.detection.plateau_detection import detect_plateau_all_exercises
from src.detection.workload_detection import detect_workload_all_muscle_groups
from src.detection.fatigue_detection import detect_fatigue
from src.detection.deload_detection import detect_deload

from src.reporting.visualization import (
    strength_progression_chart,
    weekly_volume_chart,
    sleep_chart,
    muscle_workload_chart,
    body_weight_chart,
    rpe_chart,
)
from src.reporting.report_generator import (
    daily_summary_report,
    weekly_report,
    monthly_report,
    detection_alerts_report,
)


def render(conn, user_id: int) -> None:
    st.title("Analysis & Reports")

    workout_df = load_workout_df(conn, user_id)
    recovery_df = load_recovery_df(conn, user_id)

    if workout_df.empty and recovery_df.empty:
        st.info("No data to analyze yet. Log workouts and recovery in Train and Recovery.")
        return

    # ---------- Prepare analytics-ready DataFrame ----------
    if not workout_df.empty:
        w = workout_df.copy()
        w = bulk_training_volume(w)
        w = bulk_estimated_1rm(w)
    else:
        w = pd.DataFrame()

    tab_overview, tab_charts, tab_detection, tab_reports = st.tabs(
        ["Overview", "Charts", "Detection Alerts", "Reports"]
    )

    # =====================================================================
    # Tab 1: Overview
    # =====================================================================
    with tab_overview:
        st.subheader("Headline Metrics")

        c1, c2, c3, c4 = st.columns(4)
        total_vol = float(w["volume_kg"].sum()) if not w.empty else 0.0
        total_sessions = int(w["date"].nunique()) if not w.empty else 0
        with c1:
            st.metric("Total Volume (kg)", f"{total_vol:,.0f}")
        with c2:
            st.metric("Total Sessions", total_sessions)

        if not w.empty:
            avg_rpe_all = float(w["rpe"].mean())
            with c3:
                st.metric("Avg RPE", f"{avg_rpe_all:.1f}")
            latest_e1rm = float(w["e1rm_kg"].max()) if "e1rm_kg" in w.columns else None
            with c4:
                st.metric("Best e1RM (kg)", f"{latest_e1rm:,.0f}" if latest_e1rm else "—")

        st.divider()

        st.subheader("Volume by Muscle Group")
        if not w.empty and "muscle_group" in w.columns:
            mw = bulk_muscle_workload(w, volume_col="volume_kg", muscle_col="muscle_group")
            st.dataframe(mw, hide_index=True)
        else:
            st.caption("No volume data available.")

        st.divider()

        st.subheader("Weekly Recovery Averages")
        if not recovery_df.empty:
            rs = bulk_recovery_summary(
                recovery_df,
                date_col="date",
                group_col=None,
            )
            st.dataframe(rs, hide_index=True)
        else:
            st.caption("No recovery data available.")

    # =====================================================================
    # Tab 2: Charts
    # =====================================================================
    with tab_charts:
        st.subheader("Visualizations")

        chart_choice = st.selectbox(
            "Choose a chart",
            [
                "Strength Progression (Estimated 1RM)",
                "Weekly Training Volume",
                "Sleep Duration",
                "Muscle-Group Workload",
                "Body-Weight Trend",
                "RPE Trend",
            ],
        )

        if chart_choice == "Strength Progression (Estimated 1RM)":
            st.caption("Estimated 1RM over time using the Epley formula.")
            if not w.empty:
                ex_list = ["All Exercises"] + sorted(w["exercise"].dropna().unique().tolist())
                ex_sel = st.selectbox("Filter by exercise", ex_list)
                ex_name = None if ex_sel == "All Exercises" else ex_sel
                fig = strength_progression_chart(
                    w, date_col="date", e1rm_col="e1rm_kg",
                    exercise_col="exercise" if ex_name else None,
                    exercise_name=ex_name,
                )
                st.pyplot(fig)
            else:
                st.caption("No workout data.")

        elif chart_choice == "Weekly Training Volume":
            st.caption("Total training volume per week (sets × reps × weight).")
            if not w.empty:
                fig = weekly_volume_chart(w, date_col="date")
                st.pyplot(fig)
            else:
                st.caption("No workout data.")

        elif chart_choice == "Sleep Duration":
            st.caption("Daily sleep hours over time.")
            if not recovery_df.empty:
                fig = sleep_chart(recovery_df, date_col="date", sleep_col="sleep_hours")
                st.pyplot(fig)
            else:
                st.caption("No recovery data.")

        elif chart_choice == "Muscle-Group Workload":
            st.caption("Training volume distribution by muscle group.")
            if not w.empty and "muscle_group" in w.columns:
                fig = muscle_workload_chart(w, volume_col="volume_kg", muscle_col="muscle_group")
                st.pyplot(fig)
            else:
                st.caption("No workout data.")

        elif chart_choice == "Body-Weight Trend":
            st.caption("Body weight over time.")
            if not recovery_df.empty:
                fig = body_weight_chart(recovery_df, date_col="date", weight_col="body_weight_kg")
                st.pyplot(fig)
            else:
                st.caption("No recovery data.")

        elif chart_choice == "RPE Trend":
            st.caption("Average RPE per session over time.")
            if not w.empty:
                fig = rpe_chart(w, date_col="date", rpe_col="rpe")
                st.pyplot(fig)
            else:
                st.caption("No workout data.")

    # =====================================================================
    # Tab 3: Detection Alerts
    # =====================================================================
    with tab_detection:
        st.subheader("Pattern Detection & Alerts")
        st.caption("Rule-based decision support — not a medical diagnosis.")

        if not w.empty:
            col_plateau, col_workload = st.columns(2)
            with col_plateau:
                st.write("**Strength Plateau**")
                plateau_results = detect_plateau_all_exercises(w)
                for r in plateau_results:
                    if r.get("detected"):
                        st.error(f"⚠️ {r['exercise']}: {r['explanation']}")
                        st.caption(r["guidance"])
                    else:
                        if r.get("reason") != "insufficient_data":
                            st.success(f"✓ {r['exercise']}: {r['explanation']}")
            with col_workload:
                st.write("**Workload Spike**")
                workload_results = detect_workload_all_muscle_groups(w)
                for r in workload_results:
                    if r.get("detected") and r.get("severity") == "alert":
                        st.error(f"🚨 {r['muscle_group']}: {r['explanation']}")
                        st.caption(r["guidance"])
                    elif r.get("detected"):
                        st.warning(f"⚠️ {r['muscle_group']}: {r['explanation']}")
                        st.caption(r["guidance"])
                    else:
                        if r.get("reason") not in ("insufficient_data", "insufficient_weeks"):
                            st.success(f"✓ {r['muscle_group']}: {r['explanation']}")

            st.divider()

            st.write("**Fatigue Detection**")
            if not recovery_df.empty:
                fatigue = detect_fatigue(w, recovery_df)
                if fatigue["detected"]:
                    st.error(f"🚨 Elevated Fatigue (score: {fatigue['fatigue_score']}/5)")
                    st.write(fatigue["explanation"])
                    st.caption(fatigue["guidance"])
                else:
                    st.success(f"✓ No elevated fatigue (score: {fatigue['fatigue_score']}/5)")
                    st.caption(fatigue["guidance"])

                st.divider()

                st.write("**Potential Deload Signal**")
                deload = detect_deload(w, recovery_df)
                if deload["detected"]:
                    st.warning(f"💤 Deload Signal: {deload['explanation']}")
                    st.caption(deload["guidance"])
                else:
                    st.success(f"✓ No deload signal: {deload['explanation']}")
                    st.caption(deload["guidance"])
            else:
                st.info("Add recovery data to enable fatigue and deload detection.")

            st.divider()

            # Consolidated alerts report
            all_results = plateau_results + workload_results + [fatigue] + [deload]
            alert_report = detection_alerts_report(all_results)
            st.subheader("Alert Summary")
            st.write(f"**Total alerts:** {alert_report['total_alerts']}")
            st.caption(alert_report["interpretation"])
        else:
            st.info("Log workouts to run detection.")

    # =====================================================================
    # Tab 4: Reports
    # =====================================================================
    with tab_reports:
        st.subheader("Training & Recovery Reports")

        report_type = st.selectbox("Report Type", ["Daily Summary", "Weekly Report", "Monthly Report"])

        if report_type == "Daily Summary":
            st.write("Daily workout + recovery summary for the most recent day.")
            report = daily_summary_report(w, recovery_df)
            if "error" in report:
                st.info(report["error"])
            else:
                st.write(f"**Date:** {report['date']}")
                st.write(report["interpretation"])
                st.json(report)

        elif report_type == "Weekly Report":
            st.write("Weekly training volume, sessions, RPE and recovery averages.")
            report = weekly_report(w, recovery_df)
            if "error" in report:
                st.info(report["error"])
            else:
                st.write(f"**Week of:** {report['week']}")
                st.write(report["interpretation"])
                st.json(report)

        elif report_type == "Monthly Report":
            st.write("Monthly training volume, sessions and recovery averages.")
            report = monthly_report(w, recovery_df)
            if "error" in report:
                st.info(report["error"])
            else:
                st.write(f"**Month:** {report['month']}")
                st.write(report["interpretation"])
                st.json(report)
