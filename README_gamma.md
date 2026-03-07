# SporaSync — Gamma Branch (AI Chatbot)

This branch contains the **Gemini-powered health advisor** component of SporaSync.

## My Role (Gamma)
I own the AI chatbot that takes the Spore Risk Score from Alpha and turns it into
personalized, plain-language health advice for Central Valley residents.

## Files
| File | Purpose |
|------|---------|
| `gamma_chatbot.py` | Core chatbot logic + Streamlit UI component |
| `test_gamma.py` | Standalone test page — run this to verify setup |
| `.streamlit/secrets.toml` | Your API keys (NOT pushed to GitHub) |

## Setup (do this in Phase 0)

**1. Get a Gemini API key**
- Go to https://aistudio.google.com → "Get API Key"
- Copy the key

**2. Add the key to secrets**
```
.streamlit/secrets.toml → paste your key where it says "paste-your-key-here"
```

**3. Install dependencies**
```bash
pip install google-generativeai streamlit
```

**4. Test your chatbot**
```bash
streamlit run test_gamma.py
```

You should see the chatbot UI with demo buttons and a chat input.

## Integration with app.py (Alpha merges this)

When Alpha builds `app.py`, they just need to add:
```python
from gamma_chatbot import render_chatbot

# After Alpha's risk score is calculated and Beta's map is shown:
render_chatbot(
    risk_score=calculated_risk_score,   # float from Alpha
    location=user_location,             # string from Beta's input
    case_count=delta_case_count         # int from Delta's data
)
```

## Pitch moment (Gamma speaks 2:15–3:00)
Demo button: **"🌾 Safe to work outside?"** → hits this live in front of judges.
