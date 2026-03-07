"""
app.py — CV Dust Risk Index

FIX (sidebar): Replaced cross-frame JS toggle with a pure CSS checkbox hack.
  The <input id="cvSidebarToggle" type="checkbox"> lives in the same DOM as
  the sidebar, so :checked ~ ... sibling selectors work without any JS or
  iframe boundary crossing.  The robot-button label simply toggles the
  checkbox; the sidebar slides via CSS transition alone.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import streamlit as st
import streamlit.components.v1 as components
from components.map_component import render_map
from components.info_panel import render_info_panel
from utils.session import init_session_state
from utils.styles import inject_css

st.set_page_config(
    page_title="CV Dust Risk Index",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_css()
init_session_state()

# ── Header + sidebar toggle (pure CSS checkbox — no cross-frame JS) ────────────
# The checkbox #cvSidebarToggle, the sidebar, backdrop, and main-shell must all
# be siblings (or descendents of the same parent) for the CSS ~ selector to work.
# We emit them all in one st.markdown block so they land in the same div.
st.markdown("""
<!-- Hidden checkbox — the single source of open/closed state -->
<input type="checkbox" id="cvSidebarToggle" class="sidebar-cb" aria-hidden="true">

<div class="app-header">
  <div class="header-left">
    <div class="window-title-block">
      <h1 class="app-title">Dust Risk Index — Central Valley</h1>
      <p class="app-subtitle">California · Real-time Risk Monitor</p>
    </div>
  </div>
  <div class="header-right">
    <div class="aqua-btn">
      <span class="status-dot"></span>
      <span>Live Data</span>
    </div>
    <!-- label toggles the checkbox; no JS needed -->
    <label for="cvSidebarToggle"
           class="sidebar-toggle"
           aria-label="Toggle AI assistant">
      <span class="sidebar-toggle-icon">🤖</span>
    </label>
  </div>
</div>

<!-- Sidebar and backdrop are siblings of the checkbox so CSS ~ works -->
<div class="chat-sidebar" id="cvChatSidebar">
  <div class="chat-sidebar-header">
    <span class="chat-sidebar-title">AI Assistant</span>
    <!-- close button is also a label for the same checkbox -->
    <label for="cvSidebarToggle" class="chat-sidebar-close" aria-label="Close">✕</label>
  </div>
  <div class="chat-sidebar-body">
    <div class="chat-placeholder">
      <div class="chat-placeholder-icon">🤖</div>
      <div class="chat-placeholder-text">
        Your friend's chatbot will be<br>wired in here.<br><br>
        Replace this div with the<br>chatbot component.
      </div>
    </div>
    <!-- DROP-IN: replace .chat-placeholder with chatbot component -->
  </div>
</div>

<div class="chat-backdrop" id="cvChatBackdrop">
  <!-- clicking backdrop closes sidebar on mobile -->
  <label for="cvSidebarToggle" style="display:block;width:100%;height:100%;cursor:default;"></label>
</div>
""", unsafe_allow_html=True)

# ── Main shell ─────────────────────────────────────────────────────────────────
st.markdown('<div class="main-shell" id="cvMainShell">', unsafe_allow_html=True)

render_map()
render_info_panel()

st.markdown('</div>', unsafe_allow_html=True)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-footer">
  <span>Data sources: NOAA · USDA · EPA AQS · OpenET</span>
  <span>·</span>
  <span>Refresh cadence: 6 hr</span>
</div>
""", unsafe_allow_html=True)
