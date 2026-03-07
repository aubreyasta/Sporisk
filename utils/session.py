"""
utils/session.py
Initializes and manages Streamlit session state.
"""

import streamlit as st


def init_session_state():
    """Set default session state values on first load."""
    defaults = {
        # What the user clicked on the map
        "selected_feature": None,   # dict with type, id, name, data
        "selection_type": None,     # "zip" | "county" | None

        # Current map LoD (derived from zoom, but we track it for the badge)
        "current_lod": "county",    # "county" | "zip"

        # Last loaded data timestamps (for cache invalidation)
        "data_loaded_at": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def set_selection(feature_type: str, feature_id: str, name: str, data: dict):
    """Called when a map feature is clicked."""
    st.session_state["selected_feature"] = {
        "type": feature_type,
        "id": feature_id,
        "name": name,
        "data": data,
    }
    st.session_state["selection_type"] = feature_type


def clear_selection():
    st.session_state["selected_feature"] = None
    st.session_state["selection_type"] = None
