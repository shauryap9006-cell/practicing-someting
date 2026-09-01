# Pipeline 06: Mechanistic Cascade What-If Simulation & Delay Autopsy

## 1. Purpose
Simulates corridor-wide delay propagation and ripple cascades using discrete-event simulation with priority preemption on single lines, platform contention, and same-rake turnaround linkage. Records every incurred delay minute to an exact, append-only SQLite causal event ledger (`sim_ledger`). Delivers counterfactual what-if scenario forecasting and mathematical 100% balanced delay autopsies.

---

## 2. Triggers
- **What-If Scenario Submission**: Operations controller or planner submitting a simulated disturbance via `POST /v1/simulate/what-if` (`api/routes.py:486-534`), injecting train delays or active Temporary Speed Restrictions (TSRs).
- **Gantt Day Planner Simulation**: Dispatcher simulating 24-hour schedule mutations via `POST /api/planner/simulate` (`api/planner_routes.py:41-97`) to compare baseline vs proposed delay impacts.
- **Train Detail Journey & Delay Autopsy Query**: Controller or passenger inspecting train telemetry on `web/src/pages/dashboard/TrainDetailPage.tsx` or querying `GET /v1/trains/{train_no}/autopsy` (`api/routes.py:194-271`).
- **Commercial Delay Certificate Issuance & Verification**: Passenger service agents issuing or validating digital delay certificates on `web/src/pages/dashboard/commercial/DelayCertificatePage.tsx` via `POST /api/commercial/delay-certificate` and `GET /api/commercial/delay-certificate/verify/{token}`.
- **Working Timetable (WTT) Version Comparison**: Planner validating conflict feasibility across timetable revisions on `web/src/pages/dashboard/ops/TimetablePage.tsx`.
- **CLI & Diagnostic Benchmark**: Direct simulation and test execution via `python -m engine.simulator` (`engine/simulator.py:340-359`) and `pytest tests/test_simulator.py`.

---

## 3. Mermaid Diagram

```mermaid
flowchart TD
    subgraph Triggers["Triggers & User Actions"]
        T1["What-If Scenario Injection<br/>(POST /v1/simulate/what-if)"]
        T2["Day Planner Simulation<br/>(POST /api/planner/simulate)"]
        T3["Train Delay Autopsy View<br/>(GET /v1/trains/{train_no}/autopsy)"]
        T4["Delay Certificate Issuance<br/>(POST /api/commercial/delay-certificate)"]
        T5["CLI Simulator Run<br/>(python -m engine.simulator)"]
    end

    subgraph API_Routers["API Router Layer (FastAPI)"]
        R1["api/routes.py:486<br/>(simulate_what_if)"]
        R2["api/planner_routes.py:41<br/>(simulate_day_changeset)"]
        R3["api/routes.py:194<br/>(get_train_autopsy)"]
        R4["api/commercial_routes.py<br/>(issue_delay_certificate)"]
    end

    T1 --> R1
    T2 --> R2
    T3 --> R3
    T4 --> R4
    T5 --> S1

    subgraph Corridor_Graph["Graph & Resource Mapping (engine/graph.py)"]
        S1["CascadeSimulator.run_simulation()<br/>(engine/simulator.py:57)"]
        S1 --> G1["CorridorGraph._build_graph()<br/>(engine/graph.py:27)"]
        G1 --> G2["Station Platform Capacity<br/>simpy.Resource(capacity=platforms)"]
        G1 --> G3["Single-Line Sections (single_line=1)<br/>simpy.PriorityResource(capacity=1)"]
        G1 --> G4["Double-Line Sections (single_line=0)<br/>simpy.Resource(capacity=1)"]
    end

    R1 & R2 --> S1

    subgraph Upstream_Dependencies["Upstream Physical Turnaround & Links"]
        S1 --> RK1["RakeResolver.evaluate_all_rakes()<br/>(engine/rakes.py:57)"]
        RK1 --> RK2{"Incoming Rake Delayed?<br/>actual_arr + turnaround > sched_dep"}
        RK2 -- "Yes (is_doomed=True)" --> RK3["Map Initial Departure Delay<br/>(event_type = 'RAKE_INHERIT')"]
        RK2 -- "No" --> RK4["Nominal Turnaround"]

        S1 --> DFC1["Load Freight Rake Links<br/>(trains.class = 'empty_freight')"]
        DFC1 --> DFC2["Empty Return Link Mapping<br/>(turnaround_min buffer)"]
    end

    subgraph Discrete_Event_Engine["SimPy Discrete-Event Actor Simulation (engine/simulator.py)"]
        S1 --> ACT["Spawn train_actor(train_no, priority, route)<br/>(engine/simulator.py:120)"]
        
        ACT --> E_RAKE["Step 0: RAKE_INHERIT<br/>Inherited turnaround delay from incoming rake"]
        E_RAKE --> LOOP_STN["Iterate Journey Stations & Sections"]

        LOOP_STN --> E_SHOCK{"External Delay Injected?<br/>injected[train_no][station]"}
        E_SHOCK -- "Yes" --> E_EXT["EXT_DWELL Event<br/>Injected disturbance / signal failure"]
        E_SHOCK -- "No" --> PLAT_REQ["Request Platform Resource<br/>with plat_res.request()"]

        E_EXT --> PLAT_REQ
        PLAT_REQ --> E_PLAT{"Platform Occupied?<br/>(Queue Wait Time > 0)"}
        E_PLAT -- "Yes" --> E_PW["PLATFORM_WAIT Event<br/>Queueing delay at station platform"]
        E_PLAT -- "No" --> DWELL["Scheduled Station Dwell<br/>yield env.timeout(halt_min)"]
        E_PW --> DWELL

        DWELL --> SEC_REQ["Request Section Resource<br/>sec_res.request(priority=priority)"]
        SEC_REQ --> E_HOLD{"Single-Line Priority Contention?<br/>(Queue Wait Time > 0)"}
        E_HOLD -- "Yes (Lower Priority Yields)" --> E_CH["CROSSING_HOLD Event<br/>Crossing hold in loop siding"]
        E_HOLD -- "No (Line Clear)" --> TRANSIT["Compute Section Transit Time<br/>dist / (max_speed / 60)"]
        E_CH --> TRANSIT

        TRANSIT --> E_TSR{"Active TSR on Section?<br/>(speed_factor < 1.0)"}
        E_TSR -- "Yes" --> E_TSR_EV["TSR Event<br/>tsr_run_min - normal_run_min"]
        E_TSR -- "No" --> ADVANCE["Advance Train Position<br/>yield env.timeout(runtime)"]
        E_TSR_EV --> ADVANCE

        ADVANCE --> DEST{"Destination Reached?"}
        DEST -- "No" --> LOOP_STN
        DEST -- "Yes" --> E_RET{"Loaded Freight with Return Link?"}
        E_RET -- "Yes (delay > turnaround_min)" --> E_EMPTY["EMPTY_RETURN Event<br/>Cascade delay to return rake"]
        E_RET -- "No" --> FIN["Finish Train Process"]
        E_EMPTY --> FIN
    end

    subgraph Ledger_Persistence["Exact Causal Ledger Persistence"]
        FIN --> BATCH_INS["Batch SQL INSERT INTO sim_ledger<br/>(engine/simulator.py:293)"]
        BATCH_INS --> DB_LEDGER[("sim_ledger table<br/>(run_id, sim_time, train_no, event_type, minutes, cause, counterparty, station_code)")]
    end

    subgraph Autopsy_Engine["Delay Autopsy & Aggregation Engine"]
        R3 --> A1["Query sim_ledger for train_no<br/>(api/routes.py:207 / engine/simulator.py:304)"]
        A1 --> A2{"Ledger Records Found?"}
        A2 -- "Yes" --> A3["Group By event_type, cause, station_code<br/>SUM(minutes) as total_min<br/>is_exact_accounting = True"]
        A2 -- "No (Fallback Branch)" --> A4["Query station_events historical average delays<br/>Synthesize EXT_DWELL causes<br/>is_exact_accounting = False"]
        A3 & A4 --> A5["Enforce Invariant:<br/>sum(causes.minutes) == total_predicted_delay_min"]
        A5 --> A6["DelayAutopsyResponse JSON"]
    end

    subgraph DB_Sources["Database Tables (railtwin.db)"]
        DB_STN[("stations<br/>(code, platforms, is_junction)")]
        DB_SEC[("sections<br/>(from_code, to_code, single_line, max_speed)")]
        DB_TR[("trains<br/>(train_no, priority, class)")]
        DB_RS[("route_stations<br/>(train_no, seq, sched_arr, sched_dep, halt_min, distance_km)")]
        DB_RL[("rake_links<br/>(incoming_train, outgoing_train, turnaround_min)")]
        DB_SE[("station_events<br/>(actual_arr, delay_arr_min)")]
        DB_TSR[("speed_restrictions<br/>(speed_limit_kmph, is_active)")]
    end

    G1 -.-> DB_STN & DB_SEC
    S1 -.-> DB_TR & DB_RS & DB_SEC & DB_RL
    RK1 -.-> DB_RL & DB_SE & DB_RS
    A4 -.-> DB_SE

    subgraph Frontend_Consumers["Frontend React UI Consumers (web/src/)"]
        FE_DETAIL["TrainDetailPage.tsx<br/>(Exact 100% Balanced Autopsy Ledger)"]
        FE_PLANNER["TimetablePage.tsx<br/>(Simulation Impact & Delay Delta)"]
        FE_CERT["DelayCertificatePage.tsx<br/>(Digital Delay Certificate & QR Validation)"]
        FE_OVERVIEW["OverviewPage.tsx<br/>(Network Delay KPI Cards)"]
    end

    A6 --> FE_DETAIL
    R2 --> FE_PLANNER
    R4 --> FE_CERT
    R1 --> FE_OVERVIEW
```

---

## 4. Stage-by-Stage Table

| Stage | Component / File | Key Function | Input → Output |
|---|---|---|---|
| **1. Corridor Graph & Resource Setup** | `engine/graph.py` | `CorridorGraph._build_graph()` | `(env: simpy.Environment, db: Database)` → Queries `stations` and `sections`; instantiates station platform capacity `simpy.Resource(capacity=platforms)` and single-line shared `simpy.PriorityResource(capacity=1)`. |
| **2. Same-Rake Turnaround Evaluation** | `engine/rakes.py` | `RakeResolver.evaluate_all_rakes()` | `run_date: Optional[str]` → Queries `rake_links`, `station_events`, and `route_stations`. Computes turnaround deficit $\text{earliest\_dep} - \text{sched\_dep}$; identifies doomed outgoing trains (`is_doomed = True` if delay $\ge 15\text{ min}$). Returns `List[RakeDoomStatus]`. |
| **3. Freight Empty-Return Resolution** | `engine/simulator.py` | `CascadeSimulator.run_simulation()` | `rake_links` joined with `trains` (`class = 'empty_freight'`) → Maps loaded freight trains to return empty rakes, calculating cascaded delay $\max(0, \text{accumulated\_delay} - \text{turnaround\_min})$. |
| **4. Discrete-Event Train Process Execution** | `engine/simulator.py` | `train_actor(t_no, priority, route)` | Train priority (1..5), stop sequence, injected delays, and active TSRs → SimPy generator executing sequential station dwell, section transit, and logging discrete `LedgerEvent` records. |
| **5. Single-Line Priority Preemption** | `engine/simulator.py` & `engine/graph.py` | `sec_res.request(priority=priority)` | Train priority level (Priority 1 Rajdhani holds preemption over Priority 2–5) → Yielding train waits in siding; logs `CROSSING_HOLD` with exact minutes. |
| **6. Temporary Speed Restriction (TSR) Delay** | `engine/simulator.py` | `train_actor()` | Active TSR map `active_tsrs[(from_code, to_code)] = speed_factor` → Calculates extra transit minutes $\text{tsr\_delay} = \frac{\text{normal\_run\_min}}{\text{speed\_factor}} - \text{normal\_run\_min}$; logs `TSR` event. |
| **7. Exact Ledger Persistence** | `engine/simulator.py` | `CascadeSimulator.run_simulation()` | `List[LedgerEvent]` → Executes batch SQL `INSERT INTO sim_ledger (run_id, sim_time, train_no, event_type, minutes, cause, counterparty, station_code)`. Returns `(run_id, ledger_events, total_train_delays)`. |
| **8. Causal Delay Autopsy Aggregation** | `engine/simulator.py` & `api/routes.py` | `CascadeSimulator.get_train_autopsy()` / `get_train_autopsy()` | `(run_id: str, train_no: str)` or `train_no: str` → Aggregates `sim_ledger` records by event type and cause; enforces 100% mathematical balance ($\sum \text{minutes} = \text{total\_delay}$). |
| **9. Day Planner Impact Simulation** | `api/planner_routes.py` | `simulate_day_changeset()` | `req: PlanChangesetRequest` → Runs 24h baseline simulation vs proposed plan mutations (`reassign_platform`, `retimed`, `cancel`), computing net delay savings and conflicts resolved. |

---

## 5. API Routes Table

| Method | Full Route Path | Handler Function | Required Role | Description |
|---|---|---|---|---|
| `POST` | `/v1/simulate/what-if` | `simulate_what_if` (`api/routes.py:487`) | Public / Controller | Injects simulated delay shock or section TSRs, executes SimPy cascade simulation, and returns affected trains and ledger events. |
| `POST` | `/api/planner/simulate` | `simulate_day_changeset` (`api/planner_routes.py:42`) | Authenticated User (`get_current_user`) | Runs 24-hour SimPy cascade simulation comparing baseline schedule vs proposed day planner mutations. |
| `GET` | `/v1/trains/{train_no}/autopsy` | `get_train_autopsy` (`api/routes.py:195`) | Public / Controller | Returns exact causal delay breakdown where minutes sum mathematically to total predicted delay. |
| `POST` | `/api/commercial/delay-certificate` | `issue_delay_certificate` (`api/commercial_routes.py:40`) | Authenticated User (`get_current_user`) | Issues cryptographically verifiable digital delay certificate with QR token for late-running trains. |
| `GET` | `/api/commercial/delay-certificate/{cert_no}` | `get_delay_certificate` (`api/commercial_routes.py:132`) | Public | Retrieves full details of an issued delay certificate for printing or digital presentation. |
| `GET` | `/api/commercial/delay-certificate/verify/{token}` | `verify_delay_certificate` (`api/commercial_routes.py:143`) | Public | Verifies authenticity and attributed delay minutes of an issued digital delay certificate token. |

---

## 6. Frontend Connections

| Frontend Page / Component Path (`web/src/`) | Route Called | Protocol (REST / SSE) | Polling / Interaction Behavior | UI Feature Representation |
|---|---|---|---|---|
| `pages/dashboard/TrainDetailPage.tsx` | `GET /v1/trains/{number}/autopsy`<br/>`GET /v1/trains/{number}/journey` | REST | Fetched on page mount and 5s poll via `queryKeys.train(id)`. | Visual "Delay Autopsy Ledger" card displaying 100% balanced delay decomposition (e.g. `CROSSING_HOLD`, `TSR`, `RAKE_INHERIT`, `PLATFORM_WAIT`) with exact minute counts and percentage badges. |
| `pages/dashboard/ops/TimetablePage.tsx` | `POST /api/planner/simulate` | REST | User action trigger on clicking "Version Diff" or editing timetable entries. | Schedule mutation preview showing simulated knock-on delay changes, conflicts resolved, and net savings. |
| `pages/dashboard/commercial/DelayCertificatePage.tsx` | `POST /api/commercial/delay-certificate`<br/>`GET /api/commercial/delay-certificate/verify/{token}` | REST | User Form Submission & On-Demand QR Token Verification. | Digital Travel Interruption Delay Certificate generator with printable layout, QR verification link, and official division seal. |
| `pages/dashboard/OverviewPage.tsx` | `GET /v1/network/state` | REST | 5s automatic poll. | Network KPI summary cards showing corridor-wide delay ripple propagation and active train counts. |

---

## 7. DB Tables Touched

| Table Name | Operation (Read / Write / Upsert) | Description / Columns Touched |
|---|---|---|
| `stations` | Read | Queries station codes (`code`), station names (`name`), platform counts (`platforms`), and junction flags (`is_junction`) in `engine/graph.py:31`. |
| `sections` | Read | Queries block section topology (`from_code`, `to_code`), distance (`distance_km`), single line flag (`single_line`), and maximum speed (`max_speed_kmph`) in `engine/graph.py:44` and `engine/simulator.py:78`. |
| `trains` | Read | Retrieves fleet metadata (`train_no`, `name`, `priority`, `class`) in `engine/simulator.py:81, 112`. |
| `route_stations` | Read | Queries chronological stop sequence (`seq`), scheduled arrival (`sched_arr`), departure (`sched_dep`), dwell time (`halt_min`), and cumulative distance (`distance_km`) in `engine/simulator.py:86`. |
| `rake_links` | Read | Queries same-rake turnaround links (`incoming_train`, `outgoing_train`, `station_code`, `turnaround_min`) in `engine/rakes.py:65` and `engine/simulator.py:110`. |
| `speed_restrictions` | Read | Loads active Temporary Speed Restrictions (`speed_limit_kmph`, `from_code`, `to_code`, `is_active`) to parameterize section `speed_factor`. |
| `station_events` | Read | Fetches actual arrival actuals (`actual_arr`, `delay_arr_min`) for same-rake turnaround evaluation in `engine/rakes.py:85` and historical segment delay fallbacks in `api/routes.py:222`. |
| `sim_ledger` | Read / Write | Appends discrete-event delay attribution records (`run_id`, `sim_time`, `train_no`, `event_type`, `minutes`, `cause`, `counterparty`, `station_code`) in `engine/simulator.py:294`; queried by `engine/simulator.py:308` and `api/routes.py:208`. |

---

## 8. Failure & Fallback Resilience

1. **Absence of Active Simulation in `sim_ledger` (Historical Fallback Branch)**:
   - When `GET /v1/trains/{train_no}/autopsy` is queried for a train without recent SimPy records in `sim_ledger`, the route handler (`api/routes.py:218-249`) automatically queries historical station delay averages from `station_events`. It synthesizes `EXT_DWELL` causal items and explicitly sets `is_exact_accounting = False`, ensuring the UI never encounters a 404 or null state.
2. **Simulation Engine Error Recovery**:
   - In `api/planner_routes.py:52-56`, the baseline SimPy execution is wrapped in a `try-except` block. If graph construction or discrete-event execution fails due to missing route records, the system falls back to a deterministic nominal baseline delay of `320.0` minutes, allowing differential mutation evaluation to proceed safely.
3. **Strict Bounded Simulation Horizon**:
   - The SimPy simulation environment enforces an explicit chronological termination ceiling `env.run(until=simulation_hours * 60.0)` (default 8.0h in What-If API, 12.0h in `engine/simulator.py:289`, 24.0h in `api/planner_routes.py:53`). This eliminates infinite loops, resource deadlocks, or runaway memory allocation in priority queues.
4. **Turnaround Buffer Slack Absorption**:
   - If an incoming rake arrives late but the incurred delay is less than or equal to the scheduled turnaround slack buffer ($\text{delay\_arr} \le \text{turnaround\_min}$), the outgoing departure delay is clamped to zero ($\max(0, \text{delay} - \text{turnaround})$), preventing false positive cascade propagations.

---

## 9. Latency / SLA Constants (Code-Verified)

- **12-Hour Full Corridor Multi-Train SimPy Simulation**: **< 200 ms (typically 120–180 ms)** (`engine/simulator.py:289`, `tests/test_simulator.py:42`).
- **24-Hour Day Planner Cascade Simulation**: **< 250 ms** (`api/planner_routes.py:53`).
- **Delay Autopsy Retrieval Query (`GET /v1/trains/{train_no}/autopsy`)**: **< 10 ms** (`scripts/perf_bench.py:124`, `api/routes.py:194`).
- **Mathematical Exactness Invariant**: **$\sum \text{minutes}_i \equiv \text{Total Attributed Delay}$ (100% exact causal balance with zero unexplained residual)** (`tests/test_simulator.py:42-65`, `engine/simulator.py:5`).
- **Cascade Ripple Propagation Benchmark**: **Injecting +120m shock at CNB causes cascades across $\ge 3$ trains with `CROSSING_HOLD` and `RAKE_INHERIT` events** (`tests/test_simulator.py:67-84`).
- **Standard Rake Turnaround Buffer**: **240 minutes (4.0 hours)** (`data/schema.sql:62`, `tests/test_simulator.py:38`).
- **Default What-If Simulation Window**: **8.0 hours** (`api/routes.py:504`).
- **Day Planner Simulation Window**: **24.0 hours** (`api/planner_routes.py:53`).
