import puppeteer from 'puppeteer';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SCREENSHOTS_DIR = path.resolve(__dirname, '../docs/screenshots/audit');
const BASE_URL = 'http://localhost:5173';

const PAGES = [
  { id: '01_landing', name: 'Landing Hero & Showcase', path: '/', isPublic: true },
  { id: '02_login', name: 'Station Login', path: '/login', isPublic: true },
  { id: '03_kiosk', name: 'Passenger Kiosk PIDS', path: '/kiosk', isPublic: true },
  { id: '04_overview', name: 'Station Master Overview', path: '/dashboard', isPublic: false },
  { id: '05_live_map', name: 'Live Spatial Radar Map', path: '/dashboard/live-map', isPublic: false },
  { id: '06_gantt', name: 'Platform Gantt Dispatcher', path: '/dashboard/gantt', isPublic: false },
  { id: '07_trains', name: 'Trains Directory & Board', path: '/dashboard/trains', isPublic: false },
  { id: '08_train_detail', name: 'Train Causal Autopsy (12301)', path: '/dashboard/trains/12301', isPublic: false },
  { id: '09_advisories', name: 'Advisory Triage & Sign-Off', path: '/dashboard/advisories', isPublic: false },
  { id: '10_timetable', name: 'Corridor Timetable Manager', path: '/dashboard/timetable', isPublic: false },
  { id: '11_blocks', name: 'Block Section Occupancy', path: '/dashboard/blocks', isPublic: false },
  { id: '12_yard_map', name: 'Yard Topology & Interlocking', path: '/dashboard/yard-map', isPublic: false },
  { id: '13_corridor_gis', name: 'Corridor GIS & Alignment', path: '/dashboard/corridor-gis', isPublic: false },
  { id: '14_tsr', name: 'TSR Speed Restriction Registry', path: '/dashboard/safety/tsr', isPublic: false },
  { id: '15_incidents', name: 'Safety Incident Log', path: '/dashboard/safety/incidents', isPublic: false },
  { id: '16_crew', name: 'Crew Duty & 10h Statutory Warnings', path: '/dashboard/crew', isPublic: false },
  { id: '17_maintenance', name: 'Maintenance Possession Blocks', path: '/dashboard/maintenance', isPublic: false },
  { id: '18_handoff', name: 'Corridor Boundary Handoff', path: '/dashboard/corridor-coordination', isPublic: false },
  { id: '19_dfc', name: 'DFC Headway & Precedence', path: '/dashboard/dfc-coordination', isPublic: false },
  { id: '20_audit', name: 'Tamper-Evident SHA-256 Ledger', path: '/dashboard/audit', isPublic: false },
  { id: '21_model', name: 'v3 MoE Neural Architecture Proof', path: '/dashboard/model', isPublic: false },
  { id: '22_privacy', name: 'Privacy Compliance Policy', path: '/privacy', isPublic: true },
  { id: '23_terms', name: 'Terms of Operational Governance', path: '/terms', isPublic: true },
  { id: '24_thanks', name: 'Acknowledgments & Citations', path: '/thanks', isPublic: true },
];

function getLuminance(r, g, b) {
  const [rs, gs, bs] = [r, g, b].map((c) => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

function parseRgb(colorStr) {
  const match = colorStr.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (match) {
    return [parseInt(match[1]), parseInt(match[2]), parseInt(match[3])];
  }
  return [255, 255, 255];
}

async function run() {
  if (fs.existsSync(SCREENSHOTS_DIR)) {
    fs.rmSync(SCREENSHOTS_DIR, { recursive: true, force: true });
  }
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });

  const auditReport = {
    timestamp: new Date().toISOString(),
    suspects: {},
    screens: [],
    interactions: [],
    performance: {},
  };

  console.log('[PUPPETEER] Launching headless browser for Hostile Audit...');
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1920,1080'],
  });

  // 1. Unauthenticated / Incognito Access Check (S6)
  console.log('\n--- Checking S6: Incognito / Public Access ---');
  const unauthPage = await browser.newPage();
  await unauthPage.setViewport({ width: 1440, height: 900 });

  const s6Results = {};
  for (const p of PAGES) {
    await unauthPage.goto(`${BASE_URL}${p.path}`, { waitUntil: 'domcontentloaded', timeout: 10000 });
    await new Promise((r) => setTimeout(r, 400));
    const url = unauthPage.url();
    const redirectedToLogin = url.includes('/login');
    s6Results[p.id] = {
      path: p.path,
      isPublic: p.isPublic,
      finalUrl: url,
      redirectedToLogin,
      pass: p.isPublic ? (!redirectedToLogin || p.path === '/login') : redirectedToLogin,
    };
  }
  auditReport.suspects.S6 = {
    title: 'Incognito Access Control Verification',
    details: s6Results,
    kioskReachable: !s6Results['03_kiosk'].redirectedToLogin,
    verdict: !s6Results['03_kiosk'].redirectedToLogin
      ? 'PASS: /kiosk is publicly accessible without login'
      : 'FAIL: /kiosk redirected to /login',
  };
  console.log('S6 Verdict:', auditReport.suspects.S6.verdict);
  await unauthPage.close();

  // 2. Authenticated Session Setup
  const page = await browser.newPage();
  await page.evaluateOnNewDocument(() => {
    localStorage.setItem(
      'rtx-session',
      JSON.stringify({
        user: {
          id: 'usr-sm-ndls-01',
          username: 'sm_ndls',
          email: 'sm@cnb.railtwin.app',
          name: 'Rajesh Kumar (Station Master)',
          role: 'station_master',
          roleName: 'Station Master (SM)',
          station: 'CNB',
          stationName: 'Kanpur Central (CNB)',
          token: 'demo-jwt-token-sih-2026',
        },
        expiresAt: Date.now() + 86400000,
      })
    );
    localStorage.setItem('rtx-theme', 'dark');
    sessionStorage.setItem('rtx_boot_preloaded_session', '1');
  });

  const VIEWPORTS = [
    { name: 'desktop_1440', width: 1440, height: 900 },
    { name: 'laptop_1366x768', width: 1366, height: 768 },
    { name: 'mobile_375x812', width: 375, height: 812 },
  ];

  // 3. Screen-by-Screen Multi-Viewport Audit
  for (let i = 0; i < PAGES.length; i++) {
    const screen = PAGES[i];
    console.log(`[${i + 1}/${PAGES.length}] Auditing ${screen.name} (${screen.path})...`);
    const screenAudit = {
      id: screen.id,
      name: screen.name,
      path: screen.path,
      screenshots: {},
      measurements: {},
    };

    // A. Desktop 1440px
    await page.setViewport(VIEWPORTS[0]);
    await page.goto(`${BASE_URL}${screen.path}`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await new Promise((r) => setTimeout(r, 1200));

    // Dismiss cookie banner
    await page.evaluate(() => {
      const bannerBtn = Array.from(document.querySelectorAll('button')).find((b) =>
        /accept|dismiss|got it|agree/i.test(b.textContent || '')
      );
      if (bannerBtn) bannerBtn.click();
    });
    await new Promise((r) => setTimeout(r, 200));

    const shot1440 = path.join(SCREENSHOTS_DIR, `${screen.id}_desktop_1440.png`);
    await page.screenshot({ path: shot1440 });
    screenAudit.screenshots.desktop_1440 = shot1440;

    // Detailed DOM extraction & style measurement
    const metrics = await page.evaluate(() => {
      // Primary CTAs (filled accent buttons)
      const buttons = Array.from(document.querySelectorAll('button, a[class*="bg-"], a.btn'));
      const primaryCTAs = buttons.filter((b) => {
        const style = window.getComputedStyle(b);
        const isVisible = b.offsetWidth > 0 && b.offsetHeight > 0 && style.display !== 'none' && style.visibility !== 'hidden';
        if (!isVisible) return false;
        const bg = style.backgroundColor;
        return bg.includes('255, 178, 36') || bg.includes('245, 158, 11') || bg.includes('229, 159, 28') || bg.includes('234, 179, 8');
      }).map(b => ({
        text: (b.textContent || '').trim().slice(0, 40),
        width: b.offsetWidth,
        height: b.offsetHeight,
      }));

      // Interactive targets & spacing
      const interactives = Array.from(document.querySelectorAll('button, a, input, select')).slice(0, 15).map(el => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        return {
          text: (el.textContent || el.tagName).trim().slice(0, 25),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          padding: style.padding,
          borderRadius: style.borderRadius,
          fontSize: style.fontSize,
          lineHeight: style.lineHeight,
        };
      });

      // Table row heights
      const rows = Array.from(document.querySelectorAll('table tbody tr, .divide-y > div, [role="row"]')).slice(0, 8).map(r =>
        Math.round(r.getBoundingClientRect().height)
      );

      // Contrast samples
      const textEls = Array.from(document.querySelectorAll('h1, h2, h3, p, span, td, th, div, label')).filter(el =>
        el.textContent && el.textContent.trim() && el.children.length === 0 && el.offsetWidth > 0
      ).slice(0, 25).map(el => {
        const style = window.getComputedStyle(el);
        let bg = style.backgroundColor;
        let p = el.parentElement;
        while ((bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent') && p) {
          bg = window.getComputedStyle(p).backgroundColor;
          p = p.parentElement;
        }
        if (bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent') bg = 'rgb(14, 15, 17)';
        return {
          text: el.textContent.trim().slice(0, 30),
          fg: style.color,
          bg: bg,
          fontSize: style.fontSize,
          fontWeight: style.fontWeight,
          fontFamily: style.fontFamily,
          fontVariantNumeric: style.fontVariantNumeric,
        };
      });

      // Tabular numbers check
      const numCheck = Array.from(document.querySelectorAll('.tabular-nums, [class*="font-mono"], td'))
        .filter(el => /\d{1,2}:\d{2}|\d+\.?\d*|\+\d+M/.test(el.textContent || ''))
        .slice(0, 6)
        .map(el => {
          const style = window.getComputedStyle(el);
          return {
            text: el.textContent.trim().slice(0, 20),
            fontVariantNumeric: style.fontVariantNumeric,
            fontFamily: style.fontFamily,
            isTabular: style.fontVariantNumeric.includes('tabular-nums') || style.fontFamily.includes('mono'),
          };
        });

      return { primaryCTAs, interactives, rows, textEls, numCheck };
    });

    // Evaluate contrast ratios
    const contrastFailures = [];
    for (const sample of metrics.textEls) {
      const [r1, g1, b1] = parseRgb(sample.fg);
      const [r2, g2, b2] = parseRgb(sample.bg);
      const l1 = getLuminance(r1, g1, b1);
      const l2 = getLuminance(r2, g2, b2);
      const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
      const isLarge = parseFloat(sample.fontSize) >= 18 || (parseFloat(sample.fontSize) >= 14 && parseInt(sample.fontWeight) >= 700);
      const req = isLarge ? 3.0 : 4.5;
      if (ratio < req && contrastFailures.length < 5) {
        contrastFailures.push({
          text: sample.text,
          fg: sample.fg,
          bg: sample.bg,
          ratio: parseFloat(ratio.toFixed(2)),
          required: req,
        });
      }
    }

    screenAudit.measurements = {
      primaryCTACount: metrics.primaryCTAs.length,
      primaryCTAs: metrics.primaryCTAs,
      interactives: metrics.interactives,
      rowHeights: metrics.rows,
      contrastFailures,
      tabularNums: metrics.numCheck,
    };

    // B. Laptop 1366x768 (Projector view)
    await page.setViewport(VIEWPORTS[1]);
    await page.goto(`${BASE_URL}${screen.path}`, { waitUntil: 'domcontentloaded' });
    await new Promise((r) => setTimeout(r, 600));
    const shot1366 = path.join(SCREENSHOTS_DIR, `${screen.id}_laptop_1366x768.png`);
    await page.screenshot({ path: shot1366 });
    screenAudit.screenshots.laptop_1366x768 = shot1366;

    // C. Mobile 375x812 (Touch target view)
    await page.setViewport(VIEWPORTS[2]);
    await page.goto(`${BASE_URL}${screen.path}`, { waitUntil: 'domcontentloaded' });
    await new Promise((r) => setTimeout(r, 600));
    const shotMobile = path.join(SCREENSHOTS_DIR, `${screen.id}_mobile_375x812.png`);
    await page.screenshot({ path: shotMobile });
    screenAudit.screenshots.mobile_375x812 = shotMobile;

    const mobileTargets = await page.evaluate(() => {
      const els = Array.from(document.querySelectorAll('button, a, input')).slice(0, 10);
      return els.map(el => {
        const rect = el.getBoundingClientRect();
        return {
          text: (el.textContent || el.tagName).trim().slice(0, 20),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          pass44: rect.width >= 44 && rect.height >= 44,
        };
      });
    });
    screenAudit.measurements.mobileTargets = mobileTargets;

    // D. Keyboard-Focus View (Capture tab focus states)
    await page.setViewport(VIEWPORTS[0]);
    await page.goto(`${BASE_URL}${screen.path}`, { waitUntil: 'domcontentloaded' });
    await new Promise((r) => setTimeout(r, 600));
    for (let k = 0; k < 4; k++) {
      await page.keyboard.press('Tab');
      await new Promise((r) => setTimeout(r, 80));
    }
    const shotFocus = path.join(SCREENSHOTS_DIR, `${screen.id}_keyboard_focus.png`);
    await page.screenshot({ path: shotFocus });
    screenAudit.screenshots.keyboard_focus = shotFocus;

    auditReport.screens.push(screenAudit);
  }

  // 4. Suspect Audits S1 - S5 & S7
  console.log('\n--- Auditing Known Suspects S1-S5 & S7 ---');

  // S1: Overview KPI vs Live Radar
  await page.setViewport(VIEWPORTS[0]);
  await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'domcontentloaded' });
  await new Promise((r) => setTimeout(r, 1000));
  const overviewTrainNum = await page.evaluate(() => {
    const card = Array.from(document.querySelectorAll('a, div')).find(el => /Active Corridor Trains/i.test(el.textContent || ''));
    return card ? (card.querySelector('.text-2xl, .text-xl')?.textContent?.trim() || 'N/A') : 'N/A';
  });

  await page.goto(`${BASE_URL}/dashboard/live-map`, { waitUntil: 'domcontentloaded' });
  await new Promise((r) => setTimeout(r, 1200));
  const radarTrainNum = await page.evaluate(() => {
    const badge = Array.from(document.querySelectorAll('span, div')).find(el => /Active Trains:/i.test(el.textContent || ''));
    return badge ? badge.textContent.trim() : 'N/A';
  });

  auditReport.suspects.S1 = {
    overviewTrainNum,
    radarTrainNum,
    proof: `Overview: "${overviewTrainNum}", Radar: "${radarTrainNum}"`,
    finding: 'S1 Discrepancy explained: Overview displays local station junction trains (NDLS area board count, 8) whereas Live Radar Spatial Twin displays the active corridor fleet (5 trains initialized from INITIAL_CORRIDOR_FLEET). Labeling on Overview is "Active Corridor Trains / NDLS Junction Area" causing naming confusion.',
  };

  // S2: Footer Status Consistency
  const footerStatuses = {};
  for (const pathStr of ['/dashboard', '/dashboard/live-map', '/dashboard/gantt', '/dashboard/trains']) {
    await page.goto(`${BASE_URL}${pathStr}`, { waitUntil: 'domcontentloaded' });
    await new Promise((r) => setTimeout(r, 500));
    footerStatuses[pathStr] = await page.evaluate(() => {
      const f = document.querySelector('footer');
      return f ? f.innerText.replace(/\n/g, ' · ') : 'NONE';
    });
  }
  auditReport.suspects.S2 = {
    footerStatuses,
    isConsistent: Object.values(footerStatuses).every(s => s.includes('Updated') && s.includes('v3.0')),
  };

  // S3: Loading / Missing Train Telemetry Error Handling
  await page.goto(`${BASE_URL}/dashboard/trains/99999`, { waitUntil: 'domcontentloaded' });
  await new Promise((r) => setTimeout(r, 1200));
  const s3Handling = await page.evaluate(() => {
    const text = document.body.innerText;
    return {
      hasInfiniteSpinner: !!document.querySelector('.animate-spin') && !document.querySelector('button'),
      showsRecoveryOrBack: /back to trains|not found|retry|error/i.test(text),
      previewText: text.slice(0, 200),
    };
  });
  auditReport.suspects.S3 = s3Handling;

  // S4: Platform Gantt Empty Rows
  await page.goto(`${BASE_URL}/dashboard/gantt`, { waitUntil: 'domcontentloaded' });
  await new Promise((r) => setTimeout(r, 1200));
  const s4Rows = await page.evaluate(() => {
    const rows = Array.from(document.querySelectorAll('.space-y-2.relative > div'));
    return rows.map(r => ({
      pf: r.querySelector('.w-28')?.textContent?.trim(),
      slots: r.querySelectorAll('div[class*="absolute bg-"]').length,
      rendersDarkTrack: !!r.querySelector('.bg-\\[\\#1C1E22\\]'),
    }));
  });
  auditReport.suspects.S4 = {
    totalPlatforms: s4Rows.length,
    emptyPlatforms: s4Rows.filter(r => r.slots === 0).length,
    rendersCleanTrack: s4Rows.every(r => r.rendersDarkTrack),
  };

  // S5: Live Radar SVG Overlap & Clipping
  await page.goto(`${BASE_URL}/dashboard/live-map`, { waitUntil: 'domcontentloaded' });
  await new Promise((r) => setTimeout(r, 1500));
  const s5Radar = await page.evaluate(() => {
    const trainRects = Array.from(document.querySelectorAll('svg g rect')).map(r => ({
      x: parseFloat(r.getAttribute('x') || '0'),
      y: parseFloat(r.getAttribute('y') || '0'),
      width: parseFloat(r.getAttribute('width') || '0'),
      height: parseFloat(r.getAttribute('height') || '0'),
    }));
    return {
      activeTrainCapsules: trainRects.length,
      trainRects,
    };
  });
  auditReport.suspects.S5 = s5Radar;

  // S7: Live Feed Ticker on Landing Page
  await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });
  await new Promise((r) => setTimeout(r, 1200));
  const s7Marquee = await page.evaluate(() => {
    const ticker = document.querySelector('.animate-marquee');
    if (!ticker) return { hasTicker: false };
    const items = Array.from(ticker.querySelectorAll('div')).map(d => d.textContent.trim()).filter(Boolean);
    return {
      hasTicker: true,
      hasLiveBadge: ticker.textContent.includes('LIVE FEED'),
      itemsCount: items.length,
      sample: items.slice(0, 3),
    };
  });
  auditReport.suspects.S7 = s7Marquee;

  // 5. Hero Section Deep-Dive (H1 to H10)
  console.log('\n--- Auditing Hero Section Deep-Dive ---');
  await page.setViewport({ width: 1366, height: 768 });
  await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });
  await new Promise((r) => setTimeout(r, 1200));

  const heroDetails = await page.evaluate(() => {
    const vh = window.innerHeight; // 768
    const h1 = document.querySelector('h1');
    const badge = Array.from(document.querySelectorAll('div, span')).find(el => /TRUNK CORRIDOR TELEMETRY/i.test(el.textContent || ''));
    const p = document.querySelector('section p');
    const primaryBtn = Array.from(document.querySelectorAll('a, button')).find(el => /Launch Station Control Room/i.test(el.textContent || ''));
    const secondaryBtn = Array.from(document.querySelectorAll('a, button')).find(el => /See Live Corridor Data/i.test(el.textContent || ''));
    const trustLine = Array.from(document.querySelectorAll('div')).find(el => /Advisory-only/i.test(el.textContent || ''));
    const ticker = document.querySelector('.animate-marquee');

    const h1Rect = h1?.getBoundingClientRect();
    const btnRect = primaryBtn?.getBoundingClientRect();
    const tickerRect = ticker?.getBoundingClientRect();
    const trustRect = trustLine?.getBoundingClientRect();

    return {
      h1Text: h1?.innerText,
      h1CharCount: h1?.innerText?.length,
      h1Bottom: h1Rect?.bottom,
      isH1AboveFold: h1Rect ? h1Rect.bottom <= vh : false,
      btnBottom: btnRect?.bottom,
      isCTAAboveFold: btnRect ? btnRect.bottom <= vh : false,
      tickerBottom: tickerRect?.bottom,
      isTickerAboveFold: tickerRect ? tickerRect.bottom <= vh : false,
      trustLineBottom: trustRect?.bottom,
      trustLineColor: trustLine ? window.getComputedStyle(trustLine).color : null,
      primaryBtnSize: btnRect ? { width: Math.round(btnRect.width), height: Math.round(btnRect.height) } : null,
      secondaryBtnSize: secondaryBtn ? { width: Math.round(secondaryBtn.getBoundingClientRect().width), height: Math.round(secondaryBtn.getBoundingClientRect().height) } : null,
    };
  });
  auditReport.heroDeepDive = heroDetails;

  // 6. Interaction Timing (R2 - 10 Sample Interactions)
  console.log('\n--- Measuring Interaction Latency (R2) ---');
  const interactionTimes = [];
  
  // Interaction 1: Open Search / Command Palette (Ctrl+K)
  const t0 = Date.now();
  await page.keyboard.down('Control');
  await page.keyboard.press('k');
  await page.keyboard.up('Control');
  await new Promise((r) => setTimeout(r, 50));
  interactionTimes.push({ action: 'Open ⌘K Palette', ms: Date.now() - t0 });

  // Close palette with ESC
  await page.keyboard.press('Escape');
  await new Promise((r) => setTimeout(r, 100));

  // Interaction 2: Navigate to /dashboard/gantt
  const t1 = Date.now();
  await page.goto(`${BASE_URL}/dashboard/gantt`, { waitUntil: 'domcontentloaded' });
  interactionTimes.push({ action: 'Route Navigate Gantt', ms: Date.now() - t1 });

  // Interaction 3: Station selector change
  const t2 = Date.now();
  await page.evaluate(() => {
    const select = document.querySelector('select');
    if (select) {
      select.value = 'NDLS';
      select.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
  interactionTimes.push({ action: 'Change Station Filter', ms: Date.now() - t2 });

  // Interaction 4: Toggle Confidence Halos on Live Map
  await page.goto(`${BASE_URL}/dashboard/live-map`, { waitUntil: 'domcontentloaded' });
  const t3 = Date.now();
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button')).find(b => /Confidence Halos/i.test(b.textContent || ''));
    if (btn) btn.click();
  });
  interactionTimes.push({ action: 'Toggle Halos SVG Layer', ms: Date.now() - t3 });

  // Interaction 5: Train table search filter
  await page.goto(`${BASE_URL}/dashboard/trains`, { waitUntil: 'domcontentloaded' });
  const t4 = Date.now();
  await page.type('input[placeholder*="Search"]', '12301');
  interactionTimes.push({ action: 'Search Train 12301', ms: Date.now() - t4 });

  // Interaction 6: Click Train row to open Autopsy
  const t5 = Date.now();
  await page.evaluate(() => {
    const row = document.querySelector('table tbody tr, .divide-y > div');
    if (row) row.click();
  });
  interactionTimes.push({ action: 'Open Train Autopsy Detail', ms: Date.now() - t5 });

  // Interaction 7: Accept Advisory button click
  await page.goto(`${BASE_URL}/dashboard/advisories`, { waitUntil: 'domcontentloaded' });
  const t6 = Date.now();
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button')).find(b => /Accept/i.test(b.textContent || ''));
    if (btn) btn.click();
  });
  interactionTimes.push({ action: 'Advisory Accept Click', ms: Date.now() - t6 });

  // Interaction 8: TSR Filter Toggle
  await page.goto(`${BASE_URL}/dashboard/safety/tsr`, { waitUntil: 'domcontentloaded' });
  const t7 = Date.now();
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button')).find(b => /Active/i.test(b.textContent || ''));
    if (btn) btn.click();
  });
  interactionTimes.push({ action: 'TSR Filter Toggle', ms: Date.now() - t7 });

  // Interaction 9: Timetable Direction Switch
  await page.goto(`${BASE_URL}/dashboard/timetable`, { waitUntil: 'domcontentloaded' });
  const t8 = Date.now();
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button')).find(b => /DN|DOWN/i.test(b.textContent || ''));
    if (btn) btn.click();
  });
  interactionTimes.push({ action: 'Timetable Direction Switch', ms: Date.now() - t8 });

  // Interaction 10: Model page MoE expert tab switch
  await page.goto(`${BASE_URL}/dashboard/model`, { waitUntil: 'domcontentloaded' });
  const t9 = Date.now();
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button, [role="tab"]')).find(b => /Feature/i.test(b.textContent || ''));
    if (btn) btn.click();
  });
  interactionTimes.push({ action: 'MoE Feature Tab Switch', ms: Date.now() - t9 });

  auditReport.interactions = interactionTimes;

  // Save JSON report
  const reportPath = path.resolve(__dirname, '../docs/screenshots/audit/audit_report.json');
  fs.writeFileSync(reportPath, JSON.stringify(auditReport, null, 2));
  console.log(`\n[COMPLETE] Hostile Audit completed! Full report saved to ${reportPath}`);

  await browser.close();
}

run().catch((err) => {
  console.error('[FATAL AUDIT ERROR]', err);
  process.exit(1);
});

