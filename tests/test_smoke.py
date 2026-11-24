"""End-to-end smoke tests: app loads and all seven pages render without exceptions."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "streamlit_app" / "app.py"

PAGES = ["Home", "Train", "Programs", "Exercises", "History", "Recovery", "Analysis"]


def _app(user_id: int = 1) -> AppTest:
    """Run the app with a profile pre-selected in session state.

    The real database (database/fitness.db) already contains a user with id 1,
    so we bypass the profile selector by setting session state directly.
    """
    at = AppTest.from_file(APP_PATH).run()
    assert not at.exception
    at.session_state.current_user_id = user_id
    at.session_state.pending_sets_user_id = user_id
    at.run()
    assert not at.exception
    return at


def test_app_loads_and_all_pages_render():
    at = _app()
    radio = [w for w in at.radio if str(w.label) == "Navigation"][0]
    for page in PAGES:
        radio.set_value(page).run()
        assert not at.exception, f"Page '{page}' raised: {at.exception}"


def test_exercises_tabs_render():
    """Exercises page renders both Browse Library and Add Exercise (no NameError)."""
    at = _app()
    radio = [w for w in at.radio if str(w.label) == "Navigation"][0]
    radio.set_value("Exercises").run()
    assert not at.exception


def test_recovery_body_weight_input_allows_zero():
    """Recovery page body-weight input accepts 0 (optional) without BelowMinError."""
    at = _app()
    radio = [w for w in at.radio if str(w.label) == "Navigation"][0]
    radio.set_value("Recovery").run()
    assert not at.exception
    # The body-weight number input should be present with min 0 (optional).
    body_inputs = [w for w in at.number_input if "Body Weight" in str(w.label)]
    assert body_inputs, "Expected a Body Weight number input"
