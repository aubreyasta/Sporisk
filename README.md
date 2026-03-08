# SporeRisk

Valley Fever risk prediction for California's Central Valley. Built at HackMerced XI by Team AB @ UC San Diego.

**Live:** [sporisk-main.vercel.app](https://sporisk-main.vercel.app) (React app) · [sporisk.vercel.app](https://sporisk.vercel.app) (Research paper)

## Architecture

```
frontend/          → React app (Vercel)
backend/           → FastAPI API (Railway)
  api.py           → All endpoints (risk, chat, clinics, reports)
  clinics.py       → Healthcare facility data
  vulnerable_zones.py → At-risk population zones
  data/            → Weather + air quality CSVs for env-history
  *.csv            → Model predictions (baseline + TGCN)
  Dockerfile       → Railway deployment
index.html         → Academic research paper
```

## Data sources

- **Open-Meteo** — weather + air quality (live + historical)
- **CDPH** — Valley Fever case data (2020–2026)
- **Google Gemini 2.0 Flash** — AI summaries + chatbot

## Deployment

- **Frontend:** Vercel → root directory `frontend`, env var `REACT_APP_API_URL`
- **Backend:** Railway → root directory `backend`, env vars `GEMINI_API_KEY`, `PORT`
