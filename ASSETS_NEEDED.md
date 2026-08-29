# 📦 RailTwin-X — External Assets & Requirements Checklist

To ensure seamless execution, continuous data collection, and 100% demo resilience, here is the comprehensive inventory of assets, API keys, datasets, and environment prerequisites needed from your side.

---

## 1. 🔑 API Keys & External Credentials

| Service | Purpose | Required / Optional | How to obtain / Notes |
|---|---|---|---|
| **RapidAPI (Indian Railway / IRCTC Live Running API)** | Live train running status adapter (Adapter A) | **Optional but recommended** for live scraping | Free / Freemium tier on [RapidAPI.com](https://rapidapi.com/collection/indian-railway-irctc-api) (e.g. *IRCTC Trains by Zingoy* or *Indian Railway Information*). If not provided, fallback Adapter B (web scraping) and offline Replay feed are used. |
| **Open-Meteo API Key** | Weather observations & historical archive backfill (temp, rain, humidity, fog) | **Optional** (Free tier requires NO API key) | Standard Open-Meteo free tier is rate-limited to 10k calls/day, which is more than enough for our 150-train corridor polling. |
| **Data.gov.in API Key** | Historical Indian Railways punctuality/delay statistics | **Optional** (Bonus validation) | Free registration on [data.gov.in](https://data.gov.in). |

> **Fallback Guarantee**: Even if **zero** external API keys are provided, RailTwin-X includes an offline synthetic/replay generator and direct scraper adapter, ensuring the entire ML pipeline, cascade simulator, APIs, and dashboard are fully functional offline and during 3 AM demos.

---

## 2. 📊 Datasets & Seed Data

| Asset | Format | Current Status / Source | What we need from you |
|---|---|---|---|
| **Corridor Stations & Coordinates** | CSV / SQLite | Included in our seed generator for **NDLS – CNB – LKO** corridor (New Delhi, Ghaziabad, Aligarh, Tundla, Kanpur Central, Unnao, Lucknow Charbagh, etc.) | If you want to customize or extend the corridor (e.g., NDLS – BCT Mumbai Central), provide station codes & platform counts. |
| **Timetable & Route Stations** | CSV / SQLite | Pre-configured for top ~150 trains (Rajdhani, Shatabdi, Vande Bharat, Superfast, Mail, Passenger) with scheduled arrival/departure, distances, and halts. | Any custom train schedules or official Trains-at-a-Glance (TaG) extracts you wish to inject. |
| **Same-Rake Turnaround Links (`rake_links`)** | CSV / SQLite | Pre-mapped ~15–20 real pairing dependencies (e.g., 12034 Kanpur Shatabdi → 12033 New Delhi Shatabdi). | Additional paired rake train numbers if you have specific trains you want highlighted in the demo. |
| **Historical Delay Corpus (`station_events`)** | CSV / SQLite | Generated seed corpus provided for training & proof table evaluation (~10,000–50,000 records). | Any pre-collected NTES actual arrival/departure CSV dumps you have collected so far. |

---

## 3. ⚙️ Environment & Tooling Prerequisites

| Dependency | Minimum Version | Verification Command | Purpose |
|---|---|---|---|
| **Python** | `3.10+` | `python --version` | Core backend, ML training (LightGBM), Discrete-event simulation (SimPy), FastAPI |
| **Node.js & npm** | `Node 18+`, `npm 9+` / `pnpm` | `node -v`, `npm -v` | Next.js 14+ App Router frontend dashboard |
| **Git & GitHub CLI** | `git 2.30+` | `git --version` | Version control & GitHub Actions cron workflows |

---

## 4. 🗂️ Python Package Requirements (Scope Locked)

All required dependencies are strictly within the locked scope law (no extra bloat):
```text
lightgbm>=4.0.0
simpy>=4.1.0
networkx>=3.0
pandas>=2.0.0
scikit-learn>=1.3.0
fastapi>=0.110.0
uvicorn>=0.28.0
openmeteo-requests>=1.2.0
pytest>=8.0.0
requests>=2.31.0
pydantic>=2.6.0
```

---

## 5. 🚀 Action Items for You

1. **Confirm Corridor Choice**: Default is **NDLS – CNB – LKO** (New Delhi – Kanpur – Lucknow), the busiest high-density coaching corridor on Northern / North Central Railway.
2. **RapidAPI Key (if available)**: Set `RAPIDAPI_KEY="your_key_here"` in a `.env` file when running live polling.
3. **Review & Approve Implementation Plan**: Approve the phased execution roadmap to begin Phase 1.
