# Sporisk

Valley Fever risk prediction for California's Central Valley. Built at HackMerced XI by Team AB @ UC San Diego.

**Live:** [sporisk-main.vercel.app](https://sporisk-main.vercel.app) (React app) · [sporisk.vercel.app](https://sporisk.vercel.app) (Research paper)

## Architecture

```
frontend/          → React app (Vercel), runs entirely on a bundled data snapshot
  src/data/snapshot.json → static API snapshot, see Backend/export_static.py
Backend/            → FastAPI API, scrapers, scheduler, models — kept as pipeline evidence, not deployed
  api.py           → All endpoints (risk, chat, clinics, reports)
  export_static.py → Regenerates frontend/src/data/snapshot.json from api.py
  clinics.py       → Healthcare facility data
  vulnerable_zones.py → At-risk population zones
  data/            → Weather + air quality CSVs for env-history
  *.csv            → Model predictions (baseline + TGCN)
index.html         → Academic research paper
```

## Data sources

- **Open-Meteo** — weather + air quality (historical, used to train the model)
- **CDPH** — Valley Fever case data (2020–2026)
- Summaries are rule-based (Gemini disabled in the committed snapshot)

## Deployment

The React app has no backend to call. It ships with a static snapshot of every API response it needs, generated once from the model output CSVs.

| Vercel project | Root | Serves |
|---|---|---|
| `sporisk-main` | `frontend` | React app, sporisk-main.vercel.app |
| `sporisk` | `.` | `index.html` paper, sporisk.vercel.app |

To regenerate the snapshot after changing the model or data:

```sh
cd Backend && python export_static.py
```
