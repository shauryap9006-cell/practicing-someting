# Unused & Pruned Dependencies Manifest

This document tracks every dependency removed during the production-grade codebase cleanup on 2026-09-06.
Nothing is permanently deleted; every pruned package can be immediately reinstalled using the commands provided below.

---

## 1. Web Frontend Dependencies (\web/package.json\)

| Package Name | Removed Version | Scope | Reason | Restore Command |
| :--- | :--- | :--- | :--- | :--- |
| \@radix-ui/react-dialog\ | \^1.1.2\ | \dependencies\ | Zero references or imports across \web/src\ | pm --prefix web install @radix-ui/react-dialog@^1.1.2\ |
| \@radix-ui/react-dropdown-menu\ | \^2.1.2\ | \dependencies\ | Zero references or imports across \web/src\ | pm --prefix web install @radix-ui/react-dropdown-menu@^2.1.2\ |
| \@radix-ui/react-popover\ | \^1.1.2\ | \dependencies\ | Zero references or imports across \web/src\ | pm --prefix web install @radix-ui/react-popover@^1.1.2\ |
| \@radix-ui/react-select\ | \^2.1.2\ | \dependencies\ | Zero references or imports across \web/src\ | pm --prefix web install @radix-ui/react-select@^2.1.2\ |
| \@radix-ui/react-tabs\ | \^1.1.1\ | \dependencies\ | Zero references or imports across \web/src\ | pm --prefix web install @radix-ui/react-tabs@^1.1.1\ |
| \@radix-ui/react-tooltip\ | \^1.1.4\ | \dependencies\ | Zero references or imports across \web/src\ | pm --prefix web install @radix-ui/react-tooltip@^1.1.4\ |
| \@tanstack/react-table\ | \^8.20.5\ | \dependencies\ | Zero imports in code; legacy Vite chunk target | pm --prefix web install @tanstack/react-table@^8.20.5\ |
| \@tanstack/react-virtual\ | \^3.11.2\ | \dependencies\ | Zero imports in code; legacy Vite chunk target | pm --prefix web install @tanstack/react-virtual@^3.11.2\ |
| \date-fns\ | \^4.1.0\ | \dependencies\ | Zero references or imports across \web/src\ | pm --prefix web install date-fns@^4.1.0\ |
| \echarts\ | \^5.5.1\ | \dependencies\ | Zero references in code; legacy Vite chunk target | pm --prefix web install echarts@^5.5.1\ |
| \echarts-for-react\ | \^3.0.2\ | \dependencies\ | Zero references or imports across \web/src\ | pm --prefix web install echarts-for-react@^3.0.2\ |
| \gsap\ | \^3.12.5\ | \dependencies\ | Zero imports in code; legacy Vite chunk target | pm --prefix web install gsap@^3.12.5\ |
| \lenis\ | \^1.1.18\ | \dependencies\ | Zero imports in code; legacy Vite chunk target | pm --prefix web install lenis@^1.1.18\ |
| eact-qr-code\ | \^2.0.15\ | \dependencies\ | Zero references or imports across \web/src\ | pm --prefix web install react-qr-code@^2.0.15\ |
| \zod\ | \^3.24.1\ | \dependencies\ | Zero references or imports across \web/src\ | pm --prefix web install zod@^3.24.1\ |
| \irebase\ | \^12.18.0\ | \dependencies\ | Only referenced in unimported dead \lib/firebase.ts\ | pm --prefix web install firebase@^12.18.0\ |

### Misplaced Dependencies Reclassified
| Package Name | Version | Previous Scope | New Scope | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| \puppeteer\ | \^25.9.0\ | \dependencies\ | \devDependencies\ | Headless browser test/capture automation (\web/capture.js\), not a client bundle dependency |

---

## 2. Root NPM Dependencies (\package.json\)

| Package Name | Removed Version | Reason | Restore Command |
| :--- | :--- | :--- | :--- |
| \mermaid\ | \^11.17.2\ | Zero imports in JS/TS codebase. Mermaid diagrams are rendered directly via GitHub markdown fenced code blocks | pm install mermaid@^11.17.2\ |

---

## 3. Python Backend Dependencies (equirements.txt\)

| Package Name | Removed Version | Reason | Restore Command |
| :--- | :--- | :--- | :--- |
| \openmeteo-requests\ | \>=1.2.0\ | Zero imports in Python codebase (\collector/weather.py\ directly uses equests\) | \pip install openmeteo-requests>=1.2.0\ |
