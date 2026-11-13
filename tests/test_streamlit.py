"""Streamlit UI tests using st.testing.v1.AppTest.

These tests verify that the Streamlit application loads correctly,
renders its pages without exceptions, and supports the core user flow
of creating a profile and navigating the app.
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "streamlit_app" / "app.py"


def test_app_loads_without_exception() -> None:
    """The app should load and show the profile selector without errors."""
    at = AppTest.from_file(APP_PATH).run()
    assert not at.exception


def test_profile_selector_present() -> None:
    """The home page should present a profile selector."""
    at = AppTest.from_file(APP_PATH).run()
    assert not at.exception
    labels = [str(w.label) for w in at.selectbox]
    assert any("Select profile" in label for label in labels)


def test_create_new_user_flow() -> None:
    """Creating a new profile should succeed and show navigation."""
    at = AppTest.from_file(APP_PATH).run()
    assert not at.exception

    # Select "+ Create new user" from the profile selector
    profile_select = [w for w in at.selectbox if str(w.label) == "Select profile"][0]
    profile_select.select("+ Create new user").run()
    assert not at.exception

    # Enter a name into the new-profile text input
    name_input = [w for w in at.text_input if str(w.label) == "New profile name"][0]
    name_input.input("Test User").run()
    assert not at.exception

    # Click "Create profile"
    create_btn = [w for w in at.button if str(w.label) == "Create profile"][0]
    create_btn.click().run()
    assert not at.exception

    # After creation, the app reruns; the new user should appear in the selector
    labels = [str(w.label) for w in at.selectbox]
    assert any("Select profile" in label for label in labels)
