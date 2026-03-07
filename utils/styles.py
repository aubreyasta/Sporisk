"""
utils/styles.py — Purple Aqua · Right sidebar · Clean

FIX (sidebar): JS-dependent .cv-open class replaced with CSS checkbox pattern.
  #cvSidebarToggle:checked ~ .chat-sidebar  { transform: translateX(0) }
  #cvSidebarToggle:checked ~ .chat-backdrop { opacity: 1; pointer-events: all }
  The sidebar-toggle <label> now drives the checkbox; no JS touch needed.
"""
import streamlit as st


def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=DM+Mono:wght@300;400;500&display=swap');

/* ── TOKENS ────────────────────────────────────────────────────── */
:root {
    --panel-bg:      #f0edf8;
    --panel-border:  #a898c0;
    --chrome-border: #8878a8;
    --text-1: #1a0a2e;
    --text-2: #3d2860;
    --text-3: #7060a0;
    --text-4: #b0a0cc;
    --sidebar-w: 320px;
    --header-h:  48px;
    --font-sys:  'IBM Plex Sans', -apple-system, sans-serif;
    --font-mono: 'DM Mono', Menlo, monospace;
}

/* ── GLOBAL ─────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
    font-family: var(--font-sys) !important;
    color: var(--text-1) !important;
    background:
        repeating-linear-gradient(180deg,
            rgba(255,255,255,0.055) 0px, rgba(255,255,255,0.055) 1px,
            transparent 1px, transparent 3px),
        linear-gradient(160deg, #d0c8e0 0%, #c4bcd8 50%, #bdb4d0 100%) !important;
    min-height: 100vh;
    overflow-x: hidden;
}

#MainMenu, footer, header { visibility: hidden !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { display: none !important; }
.stMarkdown { width: 100%; }
[data-testid="stAppViewContainer"] { background: transparent !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }

/* Kill Streamlit spinner/fade on the map component */
[data-testid="stCustomComponentV1"] {
    opacity: 1 !important; transition: none !important; animation: none !important;
}
[data-testid="stCustomComponentV1"] iframe {
    opacity: 1 !important; transition: none !important; animation: none !important;
}
[data-testid="stSpinner"], .stSpinner,
[data-testid="stStatusWidget"], [class*="Spinner"], [class*="skeleton"] {
    display: none !important;
}

/* ── SIDEBAR CHECKBOX — hidden, drives open/close state ─────────── */
/* The <input id="cvSidebarToggle" type="checkbox"> sits as a sibling
   BEFORE .chat-sidebar and .chat-backdrop in the DOM, so CSS ~ works. */
.sidebar-cb {
    position: absolute;
    width: 1px; height: 1px;
    opacity: 0; pointer-events: none;
    /* keep it out of flow but reachable by label */
    left: -9999px;
}

/* ── RIGHT CHAT SIDEBAR ──────────────────────────────────────────── */
.chat-sidebar {
    position: fixed;
    top: 0; right: 0; bottom: 0;
    width: var(--sidebar-w);
    z-index: 600;
    display: flex; flex-direction: column;
    transform: translateX(100%);
    transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
    background:
        repeating-linear-gradient(180deg,
            rgba(255,255,255,0.06) 0px, rgba(255,255,255,0.06) 1px,
            transparent 1px, transparent 3px),
        linear-gradient(180deg, #e8e0f8 0%, #ddd4f4 100%);
    border-left: 1px solid #c0a8e8;
    box-shadow: -4px 0 24px rgba(60,0,120,0.28);
}

/* CSS-only open: checkbox checked → sidebar slides in */
.sidebar-cb:checked ~ .chat-sidebar { transform: translateX(0); }

/* Keep legacy .cv-open class working if anything still sets it */
.chat-sidebar.cv-open { transform: translateX(0); }

.chat-sidebar-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 16px; height: var(--header-h); flex-shrink: 0;
    background-image:
        repeating-linear-gradient(180deg,
            rgba(255,255,255,0.10) 0px, rgba(255,255,255,0.10) 1px,
            transparent 1px, transparent 2px),
        linear-gradient(180deg, #d8d0ec 0%, #c4bce0 100%);
    border-bottom: 1px solid #b0a0d0;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
}
.chat-sidebar-title {
    font-family: var(--font-sys); font-size: 13px; font-weight: 600;
    color: var(--text-1); text-shadow: 0 1px 0 rgba(255,255,255,0.6);
}
/* close button is now a <label> — same visual style */
.chat-sidebar-close {
    background: none; border: none; cursor: pointer;
    font-size: 15px; color: var(--text-3); padding: 4px 8px; border-radius: 4px;
    transition: background 0.12s; display: inline-flex; align-items: center;
}
.chat-sidebar-close:hover { background: rgba(100,30,200,0.12); color: var(--text-1); }

.chat-sidebar-body {
    flex: 1; overflow-y: auto; padding: 20px 16px;
    display: flex; flex-direction: column;
}
.chat-placeholder {
    flex: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 12px;
}
.chat-placeholder-icon { font-size: 36px; opacity: 0.4; }
.chat-placeholder-text {
    font-family: var(--font-sys); font-size: 12px; text-align: center;
    color: var(--text-3); line-height: 1.6;
}

/* Backdrop — always in DOM, driven by checkbox */
.chat-backdrop {
    position: fixed; inset: 0; z-index: 590;
    background: rgba(20,0,60,0.4);
    opacity: 0; pointer-events: none;
    transition: opacity 0.28s;
    display: none;  /* shown only on mobile via media query */
}

/* Backdrop appears when sidebar is open (on mobile — see @media) */
.sidebar-cb:checked ~ .chat-backdrop {
    opacity: 1 !important; pointer-events: all !important;
}

/* Squish main content rightward on desktop */
.main-shell { transition: margin-right 0.28s cubic-bezier(0.4,0,0.2,1); }
.sidebar-cb:checked ~ * .main-shell,
.sidebar-cb:checked ~ .main-shell { margin-right: var(--sidebar-w); }

/* Toggle button: active state when checkbox checked */
.sidebar-cb:checked ~ .app-header .sidebar-toggle,
.sidebar-cb:checked + .app-header .sidebar-toggle {
    background: linear-gradient(180deg, #c070f8 0%, #9038e8 60%, #b060f0 100%) !important;
    border-color: #6010b0 !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.35), 0 1px 3px rgba(60,0,120,0.35) !important;
}

/* ── HEADER ──────────────────────────────────────────────────────── */
.app-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 16px; height: var(--header-h);
    position: sticky; top: 0; z-index: 300;
    background-image:
        repeating-linear-gradient(180deg,
            rgba(255,255,255,0.10) 0px, rgba(255,255,255,0.10) 1px,
            transparent 1px, transparent 2px),
        linear-gradient(180deg,
            #ddd8ec 0%, #ccc4e0 12%, #b8b0d0 35%,
            #c4bcd8 52%, #d0c8e4 70%, #d8d0ea 85%, #ccc4e0 100%);
    border-bottom: 1px solid var(--chrome-border);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.75), 0 1px 4px rgba(60,0,120,0.22);
}
.header-left  { display: flex; align-items: center; gap: 8px; }
.header-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

.window-title-block { display: flex; flex-direction: column; line-height: 1.15; }
.app-title {
    font-family: var(--font-sys) !important; font-size: 13px !important;
    font-weight: 600 !important; margin: 0 !important; padding: 0 !important;
    color: #1a0a2e !important; text-shadow: 0 1px 0 rgba(255,255,255,0.7) !important;
}
.app-subtitle {
    font-family: var(--font-sys) !important; font-size: 10px !important;
    font-weight: 400 !important; color: var(--text-3) !important;
    margin: 0 !important; padding: 0 !important;
}

/* Sidebar toggle — now a <label>, same visual as before */
.sidebar-toggle {
    display: flex; align-items: center; justify-content: center;
    width: 30px; height: 30px; border-radius: 5px;
    background: linear-gradient(180deg, #e8e0f8 0%, #d4cce8 100%);
    border: 1px solid #a090c0;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.7), 0 1px 2px rgba(60,0,120,0.18);
    cursor: pointer; flex-shrink: 0; transition: background 0.12s;
}
.sidebar-toggle:hover { background: linear-gradient(180deg, #f0e8ff 0%, #ddd4f4 100%); }
.sidebar-toggle-icon { font-size: 15px; line-height: 1; }

/* Aqua gel lozenge (Live Data badge) */
.aqua-btn {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 3px 14px; border-radius: 99px; border: 1px solid #5010a0;
    font-family: var(--font-sys); font-size: 11px; font-weight: 500; color: #fff;
    position: relative; overflow: hidden; cursor: default;
    background: linear-gradient(180deg, #c880f8 0%, #9840e8 30%, #7020c8 58%, #8030d8 78%, #b870f0 100%);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.55), 0 1px 3px rgba(60,0,120,0.4);
    text-shadow: 0 -1px 0 rgba(40,0,100,0.4);
}
.aqua-btn::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 52%;
    border-radius: 99px 99px 0 0;
    background: linear-gradient(180deg, rgba(255,255,255,0.52), rgba(255,255,255,0));
    pointer-events: none;
}
.status-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #d0a0ff; box-shadow: 0 0 6px #9040e0;
    animation: blink-live 2s ease-in-out infinite;
}
@keyframes blink-live { 0%,100%{opacity:1} 50%{opacity:0.35} }

/* ── MAP SECTION ─────────────────────────────────────────────────── */
.map-section { padding: 12px 16px 8px; }
.map-toolbar  { margin-bottom: 8px; }

.map-frame {
    border-radius: 6px; overflow: hidden; position: relative;
    border: 1px solid #a898c0;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.8), 0 3px 10px rgba(60,0,120,0.2);
    background: #fff;
}
.map-frame iframe { display:block; border:none !important; }

/* My Location leaflet <a> control */
.cv-loc-btn {
    display: flex !important; align-items: center !important; justify-content: center !important;
    width: 30px !important; height: 30px !important;
    font-size: 16px !important; text-decoration: none !important;
    background: linear-gradient(180deg, #f0ecff 0%, #ddd4f0 100%) !important;
    color: #3a1060 !important;
    transition: background 0.12s !important;
}
.cv-loc-btn:hover {
    background: linear-gradient(180deg, #c070f8 0%, #9038e8 100%) !important;
    color: #fff !important;
}

/* Legend */
.risk-legend { display: flex; gap: 14px; flex-wrap: wrap; padding: 6px 0 0; }
.legend-item { display: flex; align-items: center; gap: 5px;
    font-family: var(--font-sys); font-size: 10px; color: var(--text-3); }
.legend-swatch { width: 12px; height: 12px; border-radius: 2px;
    flex-shrink: 0; border: 1px solid rgba(0,0,0,0.18); }

/* ── FULL-WIDTH STATUS BAR ───────────────────────────────────────── */
.status-bar {
    display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 8px;
    padding: 10px 18px; min-height: 48px;
    border-top: 1px solid rgba(120,50,200,0.12);
    border-bottom: 1px solid rgba(120,50,200,0.12);
}
.status-bar-empty {
    background: linear-gradient(180deg, rgba(255,255,255,0.28), rgba(220,210,240,0.18));
    justify-content: center;
}
/* Active bar gets background from inline style (per risk level) */
.status-bar-active {
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 1px 6px rgba(0,0,0,0.18);
}
.status-bar-left  { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.status-bar-right { display: flex; align-items: center; flex-shrink: 0; }
.status-bar-name  { font-family: var(--font-sys); font-size: 15px; font-weight: 600; letter-spacing: 0.01em; }
.status-bar-sub   { font-family: var(--font-mono); font-size: 10px; opacity: 0.75; }
.status-bar-risk  { font-family: var(--font-sys); font-size: 12px; font-weight: 600;
    letter-spacing: 0.04em; text-transform: uppercase; }
.status-bar-hint  { font-family: var(--font-sys); font-size: 11px; color: var(--text-4); letter-spacing: 0.05em; }

.selection-type-tag {
    display: inline-flex; align-items: center;
    padding: 2px 8px; border-radius: 3px;
    font-family: var(--font-mono); font-size: 9px;
    letter-spacing: 0.1em; text-transform: uppercase;
}

/* ── INFO PANEL ──────────────────────────────────────────────────── */
.info-section { padding: 10px 16px 20px; }
.info-panel {
    background: var(--panel-bg); border-radius: 8px;
    border: 1px solid var(--panel-border);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.9), 0 3px 12px rgba(60,0,120,0.14);
    overflow: hidden;
}
.info-panel-body { padding: 14px 16px 18px; }
.info-empty {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; padding: 36px 20px; gap: 8px;
}
.info-empty-icon { font-size: 28px; opacity: 0.35; }
.info-empty-text {
    font-family: var(--font-sys); font-size: 12px; text-align: center;
    color: var(--text-3); line-height: 1.6;
}

/* ── METRIC GRID ─────────────────────────────────────────────────── */
.metrics-grid {
    display: grid; grid-template-columns: repeat(6, 1fr);
    gap: 8px; margin-bottom: 14px;
}
.metric-card {
    border-radius: 6px; border: 1px solid #c8b8e0;
    padding: 9px 10px; position: relative; overflow: hidden;
    background: linear-gradient(180deg, rgba(255,255,255,0.75) 0%, rgba(220,210,240,0.5) 100%), #ede8f8;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.9), 0 1px 3px rgba(60,0,120,0.1);
}
.metric-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, var(--metric-accent,#9040e0) 0%, rgba(255,255,255,0.6) 50%, var(--metric-accent,#9040e0) 100%);
    opacity: 0.85;
}
.metric-label { font-family: var(--font-sys); font-size: 8px; font-weight: 600;
    letter-spacing: 0.10em; text-transform: uppercase; color: var(--text-3); margin-bottom: 5px; }
.metric-value { font-family: 'IBM Plex Sans', sans-serif;
    font-size: 20px; font-weight: 300; color: #1a0a2e; line-height: 1; letter-spacing: -0.02em; }
.metric-unit  { font-family: var(--font-mono); font-size: 9px; color: var(--text-3); margin-left: 2px; }
.metric-sub   { font-family: var(--font-mono); font-size: 9px; color: var(--text-4); margin-top: 3px; }

/* ── DATA TABLE ──────────────────────────────────────────────────── */
.data-table { width: 100%; border-collapse: collapse; font-family: var(--font-mono); font-size: 11px; }
.data-table tr { border-bottom: 1px solid #ddd0f0; }
.data-table tr:last-child { border-bottom: none; }
.data-table tr:nth-child(even) td { background: rgba(120,60,200,0.035); }
.data-table td { padding: 6px; color: var(--text-2); }
.data-table td:first-child  { color: var(--text-3); font-size: 10px; letter-spacing: 0.04em; width: 44%; }
.data-table td:last-child   { color: #1a0a2e; text-align: right; font-weight: 500; }

/* ── CLEAR BUTTON — Aqua gel via CSS ─────────────────────────────── */
.clear-btn-row {
    display: flex; justify-content: center;
    padding: 16px 0 4px;
}
/* Target the actual button Streamlit renders inside .clear-btn-row */
.clear-btn-row button,
.clear-btn-row [data-testid="baseButton-secondary"],
.clear-btn-row [data-testid="stBaseButton-secondary"] {
    display: inline-flex !important; align-items: center !important; gap: 6px !important;
    padding: 6px 28px !important; border-radius: 99px !important;
    border: 1px solid #5010a0 !important; cursor: pointer !important;
    font-family: var(--font-sys) !important; font-size: 12px !important;
    font-weight: 500 !important; color: #fff !important;
    position: relative !important; overflow: hidden !important;
    background: linear-gradient(180deg,
        #c880f8 0%, #9840e8 30%, #7020c8 58%, #8030d8 78%, #b870f0 100%) !important;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.55),
        inset 0 -1px 0 rgba(40,0,100,0.25),
        0 1px 3px rgba(60,0,120,0.4) !important;
    text-shadow: 0 -1px 0 rgba(40,0,100,0.4) !important;
    min-height: unset !important; width: auto !important;
    transition: filter 0.1s !important;
}
.clear-btn-row button:hover,
.clear-btn-row [data-testid="stBaseButton-secondary"]:hover { filter: brightness(1.12) !important; }
.clear-btn-row button:active,
.clear-btn-row [data-testid="stBaseButton-secondary"]:active { filter: brightness(0.9) !important; }
.clear-btn-row::before {
    content: ''; position: absolute;
    top: 16px; left: 50%; transform: translateX(-50%);
    width: 120px; height: 18px;
    background: linear-gradient(180deg, rgba(255,255,255,0.35), rgba(255,255,255,0));
    border-radius: 99px 99px 0 0; pointer-events: none; z-index: 1;
}
.clear-btn-row { position: relative; }

/* ── FOOTER ──────────────────────────────────────────────────────── */
.app-footer {
    display: flex; gap: 10px; justify-content: center; align-items: center;
    padding: 10px; font-family: var(--font-mono); font-size: 9px;
    color: var(--text-4); letter-spacing: 0.08em;
    border-top: 1px solid #b8a8d0;
    background:
        repeating-linear-gradient(180deg,
            rgba(255,255,255,0.08) 0px, rgba(255,255,255,0.08) 1px,
            transparent 1px, transparent 3px),
        linear-gradient(180deg, #d8d0ec, #ccc4e0);
}

/* ── RADIO — purple segmented control ────────────────────────────── */
.stRadio > div {
    display: flex !important; gap: 0 !important;
    border-radius: 5px !important; overflow: hidden !important;
    border: 1px solid #a090c0 !important;
    box-shadow: inset 0 1px 2px rgba(60,0,120,0.15) !important;
    background: transparent !important; width: fit-content !important;
}
.stRadio label {
    padding: 4px 16px !important;
    font-family: var(--font-sys) !important; font-size: 11px !important;
    color: #3d2860 !important;
    background: linear-gradient(180deg, #ece8f8 0%, #dcd4f0 100%) !important;
    border-right: 1px solid #c0b0d8 !important;
    cursor: pointer !important; margin: 0 !important; border-radius: 0 !important;
    text-shadow: 0 1px 0 rgba(255,255,255,0.7) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.6) !important;
    white-space: nowrap !important;
}
.stRadio label:last-child { border-right: none !important; }
.stRadio label:has(input:checked) {
    color: #fff !important;
    background: linear-gradient(180deg, #c070f8 0%, #9038e8 38%, #7020c8 62%, #8030d8 80%, #b060f0 100%) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.4), inset 0 -1px 0 rgba(40,0,100,0.25) !important;
    text-shadow: 0 -1px 0 rgba(40,0,100,0.4) !important;
}
.stRadio input[type="radio"] { display: none !important; }

hr { border: none !important; border-top: 1px solid #d0c0e8 !important; margin: 10px 0 !important; }

::-webkit-scrollbar { width: 12px; height: 12px; }
::-webkit-scrollbar-track { background: linear-gradient(90deg, #c8c0d8, #d4cce4); }
::-webkit-scrollbar-thumb { background: linear-gradient(180deg, #c0b4d8, #a898c0);
    border-radius: 99px; border: 2px solid #d0c8e0; }
::-webkit-scrollbar-thumb:hover { background: linear-gradient(180deg, #a050e0, #7020b8); }
::-webkit-scrollbar-button { display: none; }

[data-testid="stAlert"] {
    background: linear-gradient(180deg, #f5f0ff, #ede5ff) !important;
    border: 1px solid #c090e0 !important; border-radius: 6px !important;
    color: #3a1060 !important; font-family: var(--font-sys) !important;
}

/* ── MOBILE ──────────────────────────────────────────────────────── */
@media (max-width: 768px) {
    :root { --sidebar-w: min(320px, 88vw); }
    .main-shell.sidebar-open { margin-right: 0; }
    .chat-backdrop { display: block; }       /* Show backdrop on mobile */
    .app-subtitle  { display: none; }
    .map-section   { padding: 8px 10px 6px; }
    .metrics-grid  { grid-template-columns: repeat(3, 1fr) !important; }
    .status-bar    { flex-direction: column; align-items: flex-start; gap: 6px; }
    .status-bar-right { align-self: flex-end; }
    .stRadio > div { width: 100% !important; }
    .stRadio label { flex: 1; text-align: center !important; padding: 6px 8px !important; }
    .info-section  { padding: 8px 10px 16px; }
    .info-panel-body { padding: 10px 12px 14px; }
    .data-table td { padding: 5px 4px; font-size: 10px; }
    .app-header    { padding: 0 10px; }
    .aqua-btn span:last-child { display: none; }
}
@media (max-width: 480px) {
    .metrics-grid { grid-template-columns: repeat(2, 1fr) !important; }
}
</style>
""", unsafe_allow_html=True)
