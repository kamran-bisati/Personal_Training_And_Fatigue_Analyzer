"""Main entry point for the Fitness Analytics & Training Intelligence System.

Streamlit is the presentation and input layer only. All calculations,
validation, detection and persistence live in the backend modules.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path so `database` and `src` packages
# are importable when Streamlit runs this file from streamlit_app/.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from database.db_setup import get_connection, init_db, seed_exercises
from database import repository as repo

from streamlit_app.pages import home, train, programs, exercises, history, recovery, analysis

DB_PATH = "database/fitness.db"


def _init_session_state() -> None:
    """Initialize Streamlit session state.

    The SQLite connection is intentionally NOT stored here: SQLite connections
    cannot be shared across threads, and Streamlit may run interactions on a
    different thread than the initial load. A fresh connection is created in
    main() on every run instead.
    """
    if "current_user_id" not in st.session_state:
        st.session_state.current_user_id = None
    if "pending_sets" not in st.session_state:
        st.session_state.pending_sets = []


def _user_selector(conn) -> int | None:
    """Sidebar user selector: pick an existing user or create a new one."""
    users = repo.list_users(conn)
    user_options = {u["name"]: u["id"] for u in users}
    user_options["+ Create new user"] = "new"

    selected = st.sidebar.selectbox("Select profile", list(user_options.keys()))

    if user_options[selected] == "new":
        new_name = st.sidebar.text_input("New profile name", key="new_user_name")
        if st.sidebar.button("Create profile", key="create_user_btn") and new_name.strip():
            uid = repo.create_user(conn, new_name.strip())
            st.session_state.current_user_id = uid
            st.sidebar.success(f"Profile created: {new_name.strip()}")
            st.rerun()
        return None
    else:
        st.session_state.current_user_id = user_options[selected]
        return st.session_state.current_user_id


def main() -> None:
    st.set_page_config(
        page_title="Fitness Analytics & Training Intelligence",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _init_session_state()

    # Create a fresh connection each run. SQLite connections cannot be shared
    # across threads, and Streamlit may handle interactions on a different
    # thread than the initial load.
    conn = get_connection(DB_PATH)
    init_db(conn)
    seed_exercises(conn)

    try:
        st.sidebar.title("Fitness Analytics")
        st.sidebar.caption("Python + SQLite + Streamlit")

        user_id = _user_selector(conn)

        if user_id is None:
            st.info("👋 Please select or create a profile from the sidebar to begin.")
            st.stop()

        user = repo.get_user(conn, user_id)
        st.sidebar.success(f"Profile: **{user['name']}**")

        pages = {
            "Home": home.render,
            "Train": train.render,
            "Programs": programs.render,
            "Exercises": exercises.render,
            "History": history.render,
            "Recovery": recovery.render,
            "Analysis": analysis.render,
        }

        selected_page = st.sidebar.radio("Navigation", list(pages.keys()))
        pages[selected_page](conn, user_id)

        st.sidebar.divider()
        if st.sidebar.button("Disconnect / Clear profile"):
            st.session_state.current_user_id = None
            st.session_state.pending_sets = []
            st.rerun()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
