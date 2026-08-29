# RailTwin-X System Architecture

## End-to-End System Flow

```mermaid
flowchart TB
    subgraph DataLayer["1. Data Ingestion & Storage"]
        RawEvents["IR Timetable & Station Events<br/>(Kanpur-Ghaziabad Corridor)"]
        WeatherDB["Open-Meteo Weather Store<br/>(Fog 04:00-10:00, Precip mm)"]
        HolidaysDB["Holidays Calendar Store<br/>(Gazetted Holidays & Festival Rush)"]
        SQLiteDB[("SQLite Canonical Database<br/>(Time-Split Isolated Events)")]
        
        RawEvents --> SQLiteDB
        WeatherDB --> SQLiteDB
        HolidaysDB --> SQLiteDB
    end

    subgraph FeaturePipeline["2. Leakage-Safe Snapshot Pipeline"]
        SnapGen["SnapshotGenerator<br/>(Shared Serving & Training Parity)"]
        TrackContext["TrackGraph Context Engine<br/>(Spatial Headway, Block Occupancy)"]
        Feat23["23-Feature Vector<br/>(F1-F23 Strongly Typed)"]
        
        SQLiteDB --> SnapGen
        SnapGen --> TrackContext
        TrackContext --> Feat23
    end

    subgraph MLSuite["3. Multi-Tier Machine Learning & Uncertainty"]
        subgraph Champion["Champion Tier (LightGBM)"]
            LGBDirect["Direct Quantile Boosters (q10, q50, q90)<br/>Hops <= 3 (Early Stopping 50)"]
            LGBDelta["Delta Quantile Boosters (q10, q50, q90)<br/>Autoregressive Section Rollout (>3 Hops)"]
        end
        
        subgraph Challenger["Challenger Tier (PyTorch GRU)"]
            GRU["2-Layer Non-Crossing GRU<br/>Pinball Loss + Gradient Clip (1.0)"]
        end
        
        subgraph Calibration["Conformal Calibration (CQR)"]
            CQRDirect["q_hat_direct (80% Coverage)"]
            CQRDelta["q_hat_delta (Horizon Scaled)"]
            CQRGRU["q_hat_gru (Sequential CQR)"]
        end
        
        subgraph Gate["Statistical Promotion Gate"]
            Wilcoxon["Wilcoxon Signed-Rank Test (p < 0.05)<br/>Latency < 20ms & Coverage >= 75%"]
        end
        
        Feat23 --> LGBDirect
        Feat23 --> LGBDelta
        Feat23 --> GRU
        LGBDirect --> CQRDirect
        LGBDelta --> CQRDelta
        GRU --> CQRGRU
        CQRDirect & CQRGRU --> Wilcoxon
    end

    subgraph SafetyInterlock["4. 100% Deterministic Safety Interlock (Zero ML)"]
        Rule1["1. Input Domain Sanity (Delay >= -30m, KM >= 0)"]
        Rule2["2. Priority-Dependent Recovery (15-40 km/min)"]
        Rule3["3. Monotonic Quantile Order (q10 <= q50 <= q90)"]
        Rule4["4. Absolute Delay Clamping ([-5, 720] min)"]
        Rule5["5. Cancellation Likelihood Flag (> 300 min)"]
        HumanAck["Mandatory Invariant: human_ack_required = True"]
        
        MLSuite --> Rule1 --> Rule2 --> Rule3 --> Rule4 --> Rule5 --> HumanAck
    end

    subgraph ServingAPI["5. API & Decision Intelligence Engine"]
        FastAPI["FastAPI App Server<br/>(CORS, API-Key Auth Middleware)"]
        Predictor["PredictorService<br/>(3-Tier Fallback: ML -> Hist -> Sched)"]
        ConflictEngine["ConflictScanner<br/>(Headway & Single-Line Block Engine)"]
        SimEngine["CascadeSimulator (SimPy)<br/>(Network Reoptimization & What-If)"]
        WSStream["WebSocket Stream (/v1/ws/live)<br/>(Instant State Push)"]
        
        HumanAck --> Predictor
        Predictor --> FastAPI
        ConflictEngine --> FastAPI
        SimEngine --> FastAPI
        FastAPI --> WSStream
    end

    subgraph ClientLayer["6. Next.js Controller Dashboard"]
        LiveGantt["Live Platform Gantt Chart"]
        ConflictFeed["Real-Time Conflict Alerts"]
        TimelineView["Calibrated Train Journey Timeline"]
        WhatIfSim["Interactive What-If Simulation Sandbox"]
        
        FastAPI --> ClientLayer
        WSStream --> ClientLayer
    end
```
