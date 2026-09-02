"""scripts/capture_screenshots.py
Automated high-resolution screenshot generator for RailTwin-X.
Captures all public and operational control room views at 1920x1080.
"""

import asyncio
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = Path("docs/screenshots")
BASE_URL = "http://127.0.0.1:5173"

PAGES = [
    ("01_landing_hero.png", "/", 1200),
    ("02_station_login.png", "/login", 800),
    ("03_passenger_kiosk.png", "/kiosk", 1200),
    ("04_dashboard_overview.png", "/dashboard", 1500),
    ("05_live_radar_map.png", "/dashboard/live-map", 2000),
    ("06_platform_gantt.png", "/dashboard/gantt", 1500),
    ("07_trains_directory.png", "/dashboard/trains", 1500),
    ("08_train_detail_12301.png", "/dashboard/trains/12301", 1800),
    ("09_advisory_triage.png", "/dashboard/advisories", 1500),
    ("10_timetable_manager.png", "/dashboard/timetable", 1500),
    ("11_block_sections.png", "/dashboard/blocks", 1500),
    ("12_yard_diagram.png", "/dashboard/yard-map", 1500),
    ("13_corridor_gis.png", "/dashboard/corridor-gis", 2000),
    ("14_tsr_speed_restrictions.png", "/dashboard/safety/tsr", 1500),
    ("15_safety_incidents.png", "/dashboard/safety/incidents", 1500),
    ("16_crew_duty_roster.png", "/dashboard/crew", 1500),
    ("17_maintenance_blocks.png", "/dashboard/maintenance", 1500),
    ("18_corridor_handoff.png", "/dashboard/corridor-coordination", 1500),
    ("19_dfc_precedence.png", "/dashboard/dfc-coordination", 1500),
    ("20_regulatory_audit.png", "/dashboard/audit", 1500),
    ("21_model_proof_f14.png", "/dashboard/model", 2000),
    ("22_privacy_compliance.png", "/privacy", 800),
    ("23_terms_governance.png", "/terms", 800),
    ("24_acknowledgments.png", "/thanks", 800),
]

INIT_SCRIPT = """
try {
    localStorage.setItem('rtx-session', JSON.stringify({
        user: {
            id: 'usr-sm-ndls-01',
            username: 'sm_ndls',
            email: 'sm@cnb.railtwin.app',
            name: 'Rajesh Kumar (Station Master)',
            role: 'station_master',
            roleName: 'Station Master (SM)',
            station: 'CNB',
            stationName: 'Kanpur Central (CNB)',
            token: 'demo-jwt-token-sih-2026'
        },
        expiresAt: Date.now() + 86400000
    }));
    localStorage.setItem('rtx-theme', 'dark');
    sessionStorage.setItem('rtx_boot_preloaded_session', '1');
} catch (e) {
    console.error('Failed to set localStorage', e);
}
"""


def clean_existing_screenshots():
    if SCREENSHOTS_DIR.exists():
        print(f"[CLEAN] Removing existing screenshots in {SCREENSHOTS_DIR}...", flush=True)
        shutil.rmtree(SCREENSHOTS_DIR)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[CLEAN] Fresh directory ready: {SCREENSHOTS_DIR}", flush=True)


async def main():
    clean_existing_screenshots()

    async with async_playwright() as p:
        print("[PLAYWRIGHT] Launching browser...", flush=True)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
        )

        await context.add_init_script(INIT_SCRIPT)
        page = await context.new_page()

        for idx, (filename, route, wait_ms) in enumerate(PAGES, start=1):
            target_url = f"{BASE_URL}{route}"
            print(f"[{idx}/{len(PAGES)}] Capturing {filename} ({target_url})...", flush=True)

            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
            except Exception as e:
                print(f"  [WARN] Goto timeout or error on {target_url}: {e}", flush=True)

            await page.wait_for_timeout(wait_ms)

            # Try to dismiss cookie banner
            try:
                cookie_btn = await page.query_selector("button:has-text('Accept'), button:has-text('Dismiss'), button:has-text('Got it')")
                if cookie_btn:
                    await cookie_btn.click()
                    await page.wait_for_timeout(200)
            except Exception:
                pass

            output_path = SCREENSHOTS_DIR / filename
            await page.screenshot(path=str(output_path), full_page=False)
            size_kb = output_path.stat().st_size / 1024
            print(f"  ✓ Saved: {filename} ({size_kb:.1f} KB)", flush=True)

        await browser.close()
        print(f"\n[SUCCESS] Captured all {len(PAGES)} screenshots into {SCREENSHOTS_DIR}!", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
