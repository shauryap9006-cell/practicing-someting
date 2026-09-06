# RailTwin-X Phase 4: Data Layer & Contract Audit
**Auditors:** Senior Frontend Architect · Technical Lead

---

## 4.1 `api.ts` DEEP READ & THE SILENT MOCK PROBLEM

The core communication abstraction in `web/src/lib/api.ts` is `fetchBackend<T>()` (`api.ts:293-350`):

```typescript
async function fetchBackend<T>(
  path: string,
  options: RequestInit = {},
  fallbackFn?: () => Promise<T> | T
): Promise<T> {
  // ...
  try {
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (res.ok) {
      updateStatus({ state: 'LIVE', lastSuccessfulFetch: Date.now() });
      return await res.json();
    } else {
      updateStatus({ state: 'OFFLINE', errorMessage: `HTTP ${res.status}: ${errText}` });
      if (fallbackFn) {
        return await fallbackFn(); // SILENT FALLBACK ON 4xx/5xx!
      }
      throw new Error(`API Error ${res.status} on ${path}: ${errText}`);
    }
  } catch (err: any) {
    updateStatus({ state: 'OFFLINE', errorMessage: err?.message });
    if (fallbackFn) {
      return await fallbackFn(); // SILENT FALLBACK ON NETWORK FAILURE!
    }
    throw err;
  }
}
```

### The Crucial Diagnostic: What Happens When the Backend Dies Mid-Demo?

| Page | Backend Status: LIVE | Backend Status: OFFLINE / CRASHED |
| :--- | :--- | :--- |
| `LandingPage.tsx` | Renders static benchmarks & telemetry. | Identical. Completely unaffected (static client state). |
| `OverviewPage.tsx` | Real active trains & advisories. | **SILENT MOCK DATA.** Silently falls back to `mockStore.getTrains()` & `mockStore.getStation()`. Zero offline banner or error displayed. |
| `GanttPage.tsx` | Platform berthing allocations. | **SILENT MOCK DATA.** Silently serves `mockStore.getPlatforms()`. "Re-Optimize" executes hardcoded client `setTimeout`. |
| `TrainDetailPage.tsx` | Real train journey telemetry & autopsy. | **SILENT MOCK DATA.** Reverts to `fallbackTrain` and hardcoded 4-segment autopsy (`api.ts:510-536`). |
| `LiveMapPage.tsx` | Live train positions along 785km track. | **HONEST ERROR CARD.** Shows explicit `"Telemetry service is offline"` card (`LiveMapPage.tsx:116`). |
| `ComparatorPage.tsx` | B1/B2 vs RailTwin-X quantile cone. | **SILENT CRASH / EMPTY.** Throws error caught in empty `console.error`; screen stays blank or on stale data. |
| `ForesightConsolePage.tsx`| Megaboard with Radar & Shock Lab. | **CRASH.** Silent `console.error`; leaves data null. |
| `TimeMachinePage.tsx` | Real 4-step replay with SHA-256 hashes. | **FABRICATED HASHES.** Renders `'Sealing block in SHA-256 chain...'` presented as an immutable cryptographic audit receipt! |
| `HonestModelCardPage.tsx`| Live ledger scoreboard & verification. | **FABRICATED TIP HASH.** Renders hardcoded string `'6ffbe6ab4550951b0b79bea38aa3b181927805e68d27d2f9298ff0bd6fb3031e'`. |
| `PassengerTrackerPage.tsx`| Live SSE stream / snapshot polling. | **STALE BADGE.** Displays amber connection warning badge and pauses dead reckoning loop. |
| `All 10 Operator ERP Pages`| Real or empty tables. | **SILENT MOCK DATA.** All 10 modules display mock store fixtures without warning. |

> **Architect's Assessment:** The `mockStore` fallback was intended as a dev safety net, but in production, it is a **catastrophic honesty hazard**. If a hackathon judge unplugs the network cable or kills the FastAPI process, the dashboard continues happily rendering fake trains and fake platform berthings, creating the impression of deceptive fabrication.

---

## 4.2 CONTRACT GAPS & THE `any`-TYPING TRAP

Because 23 out of 32 methods in `api.ts` return `Promise<any>` or `fetchBackend<any>`, the TypeScript compiler is completely blind to backend schema modifications:

### Case Study 1: The "causes vs cause_breakdown" Bug Class
* **Backend Endpoint:** `GET /v1/trains/{train_no}/why-late` (`api/live_routes.py:201-237`).
  * Backend returns: `cause_breakdown` (list of `{ cause_code, event_type, attributed_min, minutes, percentage }`) with a secondary alias `causes`.
* **Backend Endpoint:** `GET /v1/trains/{train_no}/autopsy` (`api/routes.py:283`).
  * Backend returns: `causes` (list of `{ event_type, minutes, cause, station_code, evidence }`).
* **Frontend Handling in `ForesightConsolePage.tsx:521-541`:**
  ```typescript
  (whyLate.cause_breakdown || whyLate.causes || []).map((cause: any) => {
    const mins = cause.attributed_min || cause.minutes || 0;
    const name = cause.cause_code || cause.event_type;
    const desc = cause.description || cause.cause;
  })
  ```
  The frontend was forced to write quadruple fallback chains (`||`) because three different backend developers exposed three different key names for the identical mathematical entity. Strong typing would have caught this at compilation.

### Case Study 2: Quantile ETA Math Re-Invented on Frontend
* **Backend Route:** `GET /v1/network/state` (`api/routes.py:307`) returns `NetworkStateResponse` containing active trains with `predicted_dest_delay_min` and `status_color`.
* **Frontend Logic in `api.ts:384-394`:**
  Instead of consuming backend quantiles, `api.ts` **fabricates its own p10, p50, p90 times in client JavaScript**:
  ```typescript
  const p50Minutes = 18 * 60 + delayMin;
  const p10 = formatClock(Math.max(0, p50Minutes - 5));
  const p50 = formatClock(p50Minutes);
  const p90 = formatClock(p50Minutes + 12);
  ```
  The frontend claims to display ML-backed conformal predictions, but `OverviewPage` and `TrainsPage` are actually displaying client-side arithmetic `(delayMin - 5)` and `(delayMin + 12)`!

### Case Study 3: The Crew Response Shape Mutation
* `api.getCrew()` in `api.ts:738`:
  ```typescript
  if (Array.isArray(res)) return res;
  if (res && Array.isArray(res.roster)) return res.roster;
  if (res && Array.isArray(res.items)) return res.items;
  return mockStore.getCrew();
  ```
  Triple defensive checks because the backend endpoint `/api/workforce/crew/roster` drifted across versions from list to object.

---

## 4.3 AUDIT OF UNMOUNTED & DEAD ENDPOINT CALLS

Cross-checking all 34 `fetchBackend` calls in `web/src/lib/api.ts` against the backend router mounted endpoints confirmed **6 UNMOUNTED / DEAD ENDPOINTS**:

1. **`POST /api/platform/reoptimize` (`api.ts:618`):**
   * *Status:* **DEAD (404).** The mounted route in `api/routes.py:321` is `POST /stations/{code}/reoptimize`.
2. **`POST /api/platform/rollback` (`api.ts:624`):**
   * *Status:* **DEAD (404).** Zero backend routes exist matching `rollback`.
3. **`POST /api/safety/tsr/{id}/lift` (`api.ts:841`):**
   * *Status:* **DEAD (404).** The backend route in `api/safety_routes.py:142` is `DELETE /api/safety/tsr/{tsr_id}`.
4. **`POST /api/section/handoffs/{id}/ack` (`api.ts:876`):**
   * *Status:* **DEAD (404).** The backend in `api/section_routes.py:206` only mounts `GET /handoffs`. No ack endpoint exists.
5. **`POST /api/workforce/crew/signon` (`api.ts:747`):**
   * *Status:* **DEAD (404).** Route does not exist under `/api/workforce/`.
6. **`POST /api/timetable/versions/{versionId}/publish` (`api.ts:804`):**
   * *Status:* **DEAD (404).** Route not mounted on backend.

### Historical GET/POST Mismatch on Demo Routes
* Previously, `/v1/demo/reset-events` was invoked via `GET` from `web/src/lib/api.ts`, while `api/demo_routes.py:76` expected `POST`.
* Current code in `api.ts:918-921` has corrected this to `{ method: 'POST' }`, but demo injection routes still lack compile-time payload validation.

---

## 4.4 STREAMING & SSE RESILIENCE AUDIT

### SSE Implementation (`web/src/lib/useLiveMotionEngine.ts:196-231`)
* Target Endpoint: `GET /v1/passenger/stream?train={trainNo}`
* **Connection Drop Behavior:**
  * Uses standard browser `EventSource`. On TCP disconnect or server restart, `EventSource` automatically attempts reconnection every 3 seconds.
  * *Failure Mode Handled:* If SSE fails completely, the engine does **NOT freeze**! Line 233 hooks into TanStack Query's 5s snapshot polling. Whenever React Query fetches `/v1/passenger/snapshot`, it feeds the fresh GPS coordinates into `handleServerFix()`.
* **Dead Reckoning (60fps rAF):**
  * When disconnected, the train continues dead reckoning along the track at smoothed speed (`useLiveMotionEngine.ts:334-375`).
  * If the connection returns and position has drifted >500m, it does not jerk awkwardly; it performs an honest 2-second cubic-bezier ease (`:170-185`) and displays a transparent notification: `"Position calibrated after signal gap (Δ 1.2 km)"`.
* **Verdict on Streaming:** High engineering quality. This dead-reckoning engine should be preserved and unified into the redesigned `/t/:trainNo` core component.

---

*End of Phase 4 Data Layer & Contract Audit. Proceed to Part B Redesign Specification.*
