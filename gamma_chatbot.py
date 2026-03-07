import google.generativeai as genai
import streamlit as st

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────
def init_gemini():
    """Initialize Gemini API. API key is stored in Streamlit secrets."""
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    return genai.GenerativeModel("gemini-1.5-flash")


# ─────────────────────────────────────────
# CORE CHATBOT LOGIC
# ─────────────────────────────────────────
def build_context(risk_score: float, location: str, case_count: int) -> str:
    """
    Build the system context that Gemini receives before answering.
    Alpha provides: risk_score
    Beta provides: location
    Delta provides: case_count (county-level Valley Fever cases)
    """
    if risk_score >= 70:
        risk_label = "HIGH"
        risk_emoji = "🔴"
    elif risk_score >= 40:
        risk_label = "MODERATE"
        risk_emoji = "🟡"
    else:
        risk_label = "LOW"
        risk_emoji = "🟢"

    context = f"""
You are SporaSync's Valley Fever Health Advisor — a knowledgeable, calm, and practical assistant
helping Central Valley residents (including farmworkers, parents, and outdoor workers) understand
their daily Valley Fever spore exposure risk.

Current environmental data:
- Location: {location}
- Spore Risk Score: {risk_score:.0f}/100 ({risk_emoji} {risk_label} RISK)
- Reported Valley Fever cases in the area this season: {case_count}

Your rules:
1. Always reference the risk score and location in your answer — make it feel personalized.
2. Give concrete, actionable advice (e.g., "wear an N95 mask", "avoid dusty fields today").
3. Use plain language — imagine you're talking to a farmworker, not a doctor.
4. Keep answers under 5 sentences unless the user asks for more detail.
5. Never say you're an AI or mention Gemini. You are SporaSync's advisor.
6. If the risk is HIGH, be direct about recommending precautions. If LOW, still remind them
   that Valley Fever can occur year-round in the Central Valley.
"""
    return context


def get_health_advice(model, user_question: str, risk_score: float, location: str, case_count: int) -> str:
    """Send user question + context to Gemini, return the response text."""
    context = build_context(risk_score, location, case_count)
    prompt = f"{context}\n\nUser question: {user_question}"

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Unable to get a response right now. Please try again. (Error: {str(e)})"


# ─────────────────────────────────────────
# STREAMLIT UI COMPONENT
# ─────────────────────────────────────────
def render_chatbot(risk_score: float, location: str, case_count: int):
    """
    Main function called by app.py to render the Gamma chatbot section.
    
    Usage in app.py:
        from gamma_chatbot import render_chatbot
        render_chatbot(risk_score=65.0, location="Merced, CA", case_count=142)
    """
    st.markdown("---")
    st.subheader("🤖 Valley Fever Health Advisor")
    st.caption("Powered by Google Gemini · Ask anything about your spore risk today")

    # Initialize Gemini model (cached so it doesn't re-init on every rerun)
    if "gemini_model" not in st.session_state:
        st.session_state.gemini_model = init_gemini()
    model = st.session_state.gemini_model

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # ── Quick demo buttons (great for the pitch!) ──
    st.markdown("**Try a question:**")
    col1, col2, col3 = st.columns(3)

    demo_questions = {
        "🌾 Safe to work outside?": "Is it safe to work outside today?",
        "😷 Do I need a mask?":     "Should I wear a mask today?",
        "👶 Kids outdoors OK?":     "Is it safe for my kids to play outside?",
    }

    for col, (label, question) in zip([col1, col2, col3], demo_questions.items()):
        with col:
            if st.button(label, use_container_width=True):
                st.session_state.pending_question = question

    # ── Chat input ──
    user_input = st.chat_input("Or type your own question...")

    # Determine which question to answer (demo button or typed input)
    question_to_answer = None
    if user_input:
        question_to_answer = user_input
    elif "pending_question" in st.session_state:
        question_to_answer = st.session_state.pop("pending_question")

    # ── Get and store response ──
    if question_to_answer:
        with st.spinner("Getting personalized advice..."):
            answer = get_health_advice(
                model, question_to_answer, risk_score, location, case_count
            )
        st.session_state.chat_history.append({"role": "user",      "text": question_to_answer})
        st.session_state.chat_history.append({"role": "assistant",  "text": answer})

    # ── Render chat history ──
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["text"])
        else:
            with st.chat_message("assistant", avatar="🍄"):
                st.write(message["text"])

    # ── Clear chat button ──
    if st.session_state.chat_history:
        if st.button("🗑️ Clear chat"):
            st.session_state.chat_history = []
            st.rerun()
