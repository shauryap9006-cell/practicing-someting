# RailTwin-X — Parked Features & Enterprise Clutter Register (12_PARKED.md)

**Project:** RailTwin-X (SIH Problem Statement 26028 — Dynamic ETA Forecast for Coaching Trains)  
**Baseline Git SHA:** `d074cc69188948644de72cad7bd4a248547e26ac`  
**Status:** FORMALLY PARKED (Hidden behind `isEnterpriseMode` demo toggle)

---

## 1. Why These Features Are Parked
Problem Statement 26028 focuses strictly on **Dynamic ETA Forecasting, Delay Cascading, Confidence Bands, and Platform Re-optimization**. 

During development, 20 extensive enterprise station management pages were created (vendor stalls, coach cleaning, lost & found, work orders Kanban, breathalyzer tests, etc.). While functional, they created severe **UI clutter (Complaint C5)** and diluted the judge demo experience away from core machine learning.

---

## 2. Parked Feature Register

| Sub-Module Name | Route Path | Implementation Files | Why Parked |
|---|---|---|---|
| 1. Assets Registry | `/dashboard/assets` | `web/src/pages/dashboard/infra/AssetsRegistryPage.tsx` | Fixed station asset maintenance (not delay forecast) |
| 2. Work Orders Kanban | `/dashboard/work-orders` | `web/src/pages/dashboard/infra/WorkOrdersPage.tsx` | Engineering work order ticketing |
| 3. Cleaning & Watering | `/dashboard/cleaning` | `web/src/pages/dashboard/infra/CleaningPage.tsx` | Coach cleaning log |
| 4. Commercial Stalls | `/dashboard/commercial/stalls` | `web/src/pages/dashboard/commercial/StallsLostFoundPage.tsx` | Platform tea stalls & vendors |
| 5. Lost & Found | `/dashboard/commercial/stalls` | `web/src/pages/dashboard/commercial/StallsLostFoundPage.tsx` | Passenger lost luggage register |
| 6. Shift Handover Memo | `/dashboard/handover` | `web/src/pages/dashboard/gov/ShiftHandoverPage.tsx` | Station Master shift checklist |
| 7. User Admin | `/dashboard/admin/users` | `web/src/pages/dashboard/gov/AdminUsersPage.tsx` | Password reset & user RBAC |
| 8. Backups & Snapshots | `/dashboard/admin/backups` | `web/src/pages/dashboard/gov/BackupsIntegrityPage.tsx` | SQLite snapshot maintenance |
| 9. Regulatory Audit Chain | `/dashboard/audit` | `web/src/pages/dashboard/AuditPage.tsx` | HMAC tamper-evident inspector |
| 10. Timetable Editor | `/dashboard/timetable` | `web/src/pages/dashboard/ops/TimetablePage.tsx` | Working timetable publisher |
| 11. Block Sections Token | `/dashboard/blocks` | `web/src/pages/dashboard/ops/BlockSectionsPage.tsx` | Token instrument line-clear |
| 12. Loco Shunting Log | `/dashboard/shunting` | `web/src/pages/dashboard/ops/ShuntingPage.tsx` | Yard loco reversal tracker |
| 13. Yard Track Schematic | `/dashboard/yard-map` | `web/src/pages/dashboard/network/YardDiagramPage.tsx` | Station track schematic SVG |
| 14. Level Crossing Gate | `/dashboard/safety/lc` | `web/src/pages/dashboard/safety/LCMonitorPage.tsx` | Road barrier gate status |
| 15. SOP Emergency Runner | `/dashboard/safety/sop` | `web/src/pages/dashboard/safety/SOPRunnerPage.tsx` | Digital disaster checklist |
| 16. Incident Register | `/dashboard/safety/incidents` | `web/src/pages/dashboard/safety/IncidentsPage.tsx` | OHE trip / trespass log |
| 17. TSR Caution Orders | `/dashboard/safety/tsr` | `web/src/pages/dashboard/safety/TSRRegistryPage.tsx` | Speed restriction manager |
| 18. Crew Duty Rosters | `/dashboard/crew` | `web/src/pages/dashboard/CrewPage.tsx` | 8-hour crew fatigue & breathalyzer |
| 19. Maintenance Blocks | `/dashboard/maintenance` | `web/src/pages/dashboard/MaintenancePage.tsx` | Track-block Gantt chart |
| 20. Inter-Station Handoff | `/dashboard/corridor-coordination` | `web/src/pages/dashboard/coord/CorridorHandoffPage.tsx` | Multi-station boundary token |

---

## 3. Core 6 Views Kept Active in Demo Mode
1. **Live Station Board (`/dashboard`)** — Real-time incoming train arrivals with ML expected ETA vs scheduled time.
2. **Train Journey Delay Timeline (`/dashboard/trains/:trainNo`)** — Stop-by-stop journey breakdown with $[p_{10}, p_{50}, p_{90}]$ confidence bands.
3. **Platform Occupancy Gantt (`/dashboard/gantt`)** — Visual berth clash detector with 1-click re-optimizer.
4. **Advisory Triage & Human ACK (`/dashboard/advisories`)** — Dispatcher alert inbox with keyboard shortcuts (A/D).
5. **Corridor GIS Map (`/dashboard/map`)** — Interactive MapLibre spatial map of train positions.
6. **Model Proof & Wilcoxon Table (`/dashboard/model`)** — Empirical backtest scorecard proving superiority over timetable recovery baseline.
