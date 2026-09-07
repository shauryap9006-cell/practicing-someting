# RailTwin-X Live Wall

**Standalone Real-Time Railway Digital Twin Mission Control Wall**

The **RailTwin-X Live Wall** is a dedicated, read-only control-room display designed for continuous wall-mounted monitoring. It operates in a single, fullscreen `100vh`/`100vw` viewport with zero navigation, zero manual login, and zero mock data. It continuously visualizes the physical state of the digital twin corridor in real-time.

---

## Quick Start (2 Commands)

```bash
# 1. Install dependencies
cd livewall && npm install

# 2. Start the dev server (port 5174)
npm run dev
```

*Note: Ensure the backend is running (`python -m uvicorn api.main:app --port 8000`). The Vite dev server automatically proxies `/v1` and `/api` to `http://localhost:8000`.*

---

## Architecture

```
                       ┌─────────────────────────────┐
                       │  RailTwin-X Backend API     │
                       │  (FastAPI on :8000)         │
                       └──────────────┬──────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            │ 1 Hz SSE Stream         │ Polling REST Endpoints  │
            │ (/v1/live/stream)       │ (/v1/meta/clock, etc.)  │
            ▼                         ▼                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        livewall/src/lib/feed.ts                        │
│             Unified Ingestion, Stale & Offline Detector                │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        livewall/src/lib/motion.ts                      │
│     60fps Kinematic Dead-Reckoning & Cubic Ease Drift Corrector        │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           ▼                         ▼                         ▼
 ┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
 │   HeaderBar.tsx   │     │  TrainChips.tsx   │     │  CorridorMap.tsx  │
 │ (Clock, Counts)   │     │  (Active Marquee) │     │ (★ 60fps SVG Map) │
 └───────────────────┘     └───────────────────┘     └───────────────────┘
           │                         │                         │
           └─────────────────────────┼─────────────────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
           ┌───────────────────┐           ┌───────────────────┐
           │ StationBoard.tsx  │           │ EventTicker.tsx   │
           │ (30s Auto-Cycle)  │           │ (Live Dispatch)   │
           └───────────────────┘           └───────────────────┘
                     │                               │
                     └───────────────┬───────────────┘
                                     ▼
                           ┌───────────────────┐
                           │ CongestionBar.tsx │
                           │ (Block Occupancy) │
                           └───────────────────┘
```

---

## Consumed APIs

| Endpoint | Method | Protocol | Purpose |
|---|---|---|---|
| `/v1/live/stream` | GET | SSE | 1 Hz real-time kinematic position updates of all corridor trains |
| `/v1/meta/clock` | GET | REST (every 3s) | Virtual simulation clock timestamp, acceleration multiplier, and liveness |
| `/v1/network/state` | GET | REST (every 10s) | Active fleet count, delayed train counts, conflicts, and train metadata |
| `/v1/corridor/congestion-radar` | GET | REST (every 10s) | Block section occupancies and chokepoint capacity percentages |
| `/api/board/live` | GET | REST (every 10s) | Station arrival and departure boards (auto-cycling every 30s) |
| `/v1/live/events/recent` | GET | REST (every 10s) | Unified operational dispatch log (arrivals, departures, delay shifts, shocks, TSRs) |
| `/v1/meta/stations` | GET | REST (on mount) | Dynamic corridor stations metadata, names, and geographic coordinates |
| `/v1/demo/inject-event` | POST | REST (Shift+S) | Optional Dev Panel for live demo shock injection (Fog, Signal Hold, TSR) |
| `/v1/demo/reset-events` | POST | REST (Shift+S) | Optional Dev Panel to reset injected shocks |

---

## Key Features

1. **60 FPS Dead-Reckoning**: Between 1 Hz SSE pulses, trains smoothly glide along the dual-track SVG corridor via `requestAnimationFrame` with cubic ease-out drift correction.
2. **Fixed 100vh/100vw Viewport**: Exact 5-row CSS grid layout tailored for control-room monitors (`8vh`, `7vh`, `45vh`, `28vh`, `12vh`) without scrollbars at both 1920×1080 and 1366×768.
3. **Zero-Mock Telemetry**: Every single data point is sourced live from the running simulation backend.
4. **Auto-Recovery & Stale Detection**: If SSE pulses pause for >10s, the UI dims to amber STALE state. If the backend goes down, the UI dims to 40% with a red OFFLINE status indicator, and automatically recovers to LIVE as soon as the backend reconnects.
5. **Auto-Cycling Station Board**: Displays upcoming arrivals and departures, cycling through corridor stations every 30 seconds with animated progress indication.
6. **Live Operational Dispatch Ticker**: Rolling log of newest arrivals, departures, speed restrictions, and delay shifts.
7. **Developer Demo Trigger (Shift+S)**: A hidden panel to inject operational shocks and watch the live wall react dynamically in real-time.
