"""
utils/session.py — Session state management
"""
from __future__ import annotations
import streamlit as st


def init_session_state():
    defaults = {
        "selected_feature": None,
        "selection_type":   None,
        "current_lod":      "county",
        "data_loaded_at":   None,
        "chat_messages":    [],
        # User's detected county (set once at startup from location)
        # Value: county name string, "OUT_OF_RANGE", or None (not yet detected)
        "user_county":      None,
        # Whether the county picker popover is open
        "county_picker_open": False,
        # Which metric chart is open (metric key string or None)
        "active_chart":       None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def set_selection(feature_type: str, feature_id: str, name: str, data: dict):
    st.session_state["selected_feature"] = {
        "type": feature_type,
        "id":   feature_id,
        "name": name,
        "data": data,
    }
    st.session_state["selection_type"] = feature_type


def clear_selection():
    st.session_state["selected_feature"] = None
    st.session_state["selection_type"]   = None
