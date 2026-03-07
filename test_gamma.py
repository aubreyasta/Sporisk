"""
test_gamma.py — Run this file to verify your Gemini setup works
before integrating with the full app.

Usage:
    streamlit run test_gamma.py
"""

import streamlit as st
from gamma_chatbot import render_chatbot

st.set_page_config(page_title="Gamma Chatbot Test", page_icon="🍄")
st.title("🧪 Gamma Chatbot — Standalone Test")
st.info("This is a test page. In the real app, risk_score and location come from Alpha & Beta.")

# ── Sliders to simulate data from Alpha/Beta ──
st.sidebar.header("Simulate Team Data")
risk_score = st.sidebar.slider("Spore Risk Score (from Alpha)", 0, 100, 65)
location   = st.sidebar.text_input("Location (from Beta)", value="Merced, CA")
case_count = st.sidebar.number_input("Valley Fever Cases (from Delta)", value=142, min_value=0)

# ── Render the chatbot ──
render_chatbot(risk_score=risk_score, location=location, case_count=case_count)
