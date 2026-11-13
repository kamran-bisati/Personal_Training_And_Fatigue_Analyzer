"""Recovery page: daily recovery input form."""

from __future__ import annotations

from datetime import date
import streamlit as st

from database import repository as repo


def render(conn, user_id: int) -> None:
    st.title("Recovery — Daily Log")

    # ---------- Input form ----------
    st.subheader("Enter Recovery Data")
    col1, col2 = st.columns(2)
    with col1:
        log_date = st.date_input("Date", value=date.today())
        sleep_hours = st.number_input("Sleep (hours)", min_value=0.0, max_value=24.0, value=7.5, step=0.5)
    with col2:
        body_weight_kg = st.number_input("Body Weight (kg)", min_value=30.0, max_value=300.0, value=0.0, step=0.5)
        soreness = st.number_input("Muscle Soreness (1-10)", min_value=1, max_value=10, value=3, step=1)
        energy = st.number_input("Energy Level (1-10)", min_value=1, max_value=10, value=8, step=1)

    log_date_str = log_date.isoformat()

    # Check if recovery already exists for this date
    existing = repo.get_recovery(conn, user_id, log_date_str)
    if existing:
        st.info(f"A recovery log already exists for {log_date_str}. Submitting will update it.")

    if st.button("Save Recovery", type="primary", width="stretch"):
        try:
            # Use 0.0 as sentinel for "not provided" for body weight
            bw = body_weight_kg if body_weight_kg > 0 else None
            log_id = repo.log_recovery(
                conn=conn,
                user_id=user_id,
                log_date=log_date_str,
                sleep_hours=float(sleep_hours),
                body_weight_kg=bw,
                soreness=int(soreness),
                energy=int(energy),
            )
            action = "updated" if existing else "saved"
            st.success(f"Recovery {action}! (ID: {log_id})")
            st.rerun()
        except Exception as exc:
            st.error(f"Failed to save recovery: {exc}")

    st.divider()

    # ---------- Recent recovery ----------
    st.subheader("Recent Recovery Logs")
    rows = repo.list_recovery_by_user(conn, user_id, limit=10)
    if rows:
        for r in rows:
            bw_str = f"{r['body_weight_kg']} kg" if r["body_weight_kg"] is not None else "—"
            st.write(
                f"• {r['log_date']}: sleep {r['sleep_hours']} h, "
                f"weight {bw_str}, soreness {r['soreness']}/10, energy {r['energy']}/10"
            )
    else:
        st.caption("No recovery logs yet.")
