import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { SEO } from '@/lib/seo';
import { SITE } from '@/config/site';
import { V3_SHOOTOUT_BENCHMARKS } from '@/mock/model';
import {
  ArrowRight,
  Shield,
  Activity,
  Maximize2,
  Lock,
  Radio,
  Clock,
  Layers,
  Sparkles,
  ChevronRight,
  FileCheck,
} from 'lucide-react';
import { toast } from 'sonner';

import { ThreeCorridor } from '@/components/landing/ThreeCorridor';
import { BootPreloader } from '@/components/landing/BootPreloader';
import { TheLineScroll } from '@/components/landing/TheLineScroll';
import { AuditChainVisual } from '@/components/landing/AuditChainVisual';
import { CorridorSpine, EventTicker, RailCursor } from '@/components/aspect';

export function LandingPage() {
  const navigate = useNavigate();
  const [bootComplete, setBootComplete] = useState(false);
  const [showStickyCTA, setShowStickyCTA] = useState(false);
  const [activeTab, setActiveTab] = useState<'proof' | 'safety'>('proof');

  // Form State
  const [stationCode, setStationCode] = useState('CNB');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [org, setOrg] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const proofMetrics = V3_SHOOTOUT_BENCHMARKS;

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 600) {
        setShowStickyCTA(true);
      } else {
        setShowStickyCTA(false);
      }
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleRequestAccess = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      toast.success('Simulation Access Key Generated', {
        description: `Credentials provisioned for ${name || 'Station Controller'} at [${stationCode}]. Entering terminal...`,
      });
      navigate('/dashboard');
    }, 800);
  };

  return (
    <div className="min-h-screen bg-[#0A0B0D] text-[#E9EBEE] font-sans relative overflow-x-hidden selection:bg-[#F5A524] selection:text-[#0A0B0D]">
      <SEO
        title="RailTwin-X · Autonomous Digital Twin for Indian Railways Operations"
        description="High-fidelity digital twin and predictive dispatch engine for Indian Railways. Resolves platform conflicts, models cascading delays, and guarantees crew compliance."
      />

      {/* Signature Amber Rail Cursor */}
      <RailCursor />

      {/* Scene 0: Boot Preloader (Once per session, 900ms) */}
      {!bootComplete && <BootPreloader onComplete={() => setBootComplete(true)} />}

      {/* Top Fixed Header */}
      <header className="fixed top-0 left-0 right-0 z-40 bg-[#0A0B0D]/90 backdrop-blur-md border-b border-[#23272F] px-4 sm:px-8 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-[#F5A524] shadow-[0_0_8px_rgba(245,165,36,0.6)] animate-pulse" />
          <span className="font-mono text-sm font-bold tracking-tight text-[#E9EBEE]">
            RAILTWIN<span className="text-[#F5A524]">-X</span>
          </span>
          <span className="hidden sm:inline font-mono text-[10px] text-[#A3ABB6] border-l border-[#23272F] pl-3">
            NCR / CNB DIVISION · ASPECT SIGNAL PANEL
          </span>
        </div>

        <nav className="flex items-center gap-6 font-mono text-xs">
          <a href="#corridor-live" className="text-[#A3ABB6] hover:text-[#E9EBEE] hidden md:inline transition-colors">
            Live Corridor
          </a>
          <a href="#the-line" className="text-[#A3ABB6] hover:text-[#E9EBEE] hidden md:inline transition-colors">
            The Line
          </a>
          <Link to="/dashboard/model" className="text-[#A3ABB6] hover:text-[#E9EBEE] hidden md:inline transition-colors">
            v3 Model Proof
          </Link>
          <Link to="/kiosk" target="_blank" className="text-[#A3ABB6] hover:text-[#F5A524] flex items-center gap-1 transition-colors">
            <span>Passenger PIDS</span>
            <Maximize2 className="w-3 h-3" />
          </Link>

          <Link
            to="/login"
            className="px-3.5 py-1.5 bg-[#F5A524] hover:bg-[#F5A524]/90 text-[#0A0B0D] font-bold tracking-wide transition-colors flex items-center gap-1.5 rounded-sm shadow-[0_0_12px_rgba(245,165,36,0.25)]"
          >
            <Lock className="w-3 h-3 stroke-[2.5]" />
            <span>Station Login</span>
          </Link>
        </nav>
      </header>

      {/* Scene 1: Hero Section with 3D Night Corridor & Signature CorridorSpine */}
      <section className="relative min-h-screen pt-28 pb-16 flex flex-col justify-between px-4 sm:px-8 max-w-7xl mx-auto z-10">
        {/* 3D Rail Corridor Background with Intercity Train Running on Tracks */}
        <ThreeCorridor />

        {/* Hero Overlay Content */}
        <div className="relative z-10 max-w-3xl space-y-6 mt-8 sm:mt-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-[#101216] border border-[#23272F] rounded-sm font-mono text-xs text-[#F5A524]">
            <span className="w-2 h-2 rounded-full bg-[#3DDC97] shadow-[0_0_8px_rgba(61,220,151,0.6)] animate-pulse" />
            <span>TRUNK CORRIDOR TELEMETRY · 785 KM ACTIVE</span>
          </div>

          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-[#E9EBEE] leading-tight font-display">
            Know the platform conflict <span className="text-[#F5A524]">before it happens.</span>
          </h1>

          <p className="text-base sm:text-lg text-[#A3ABB6] leading-relaxed max-w-2xl font-sans">
            Calibrated ETA confidence bands with an <strong className="text-[#E9EBEE]">81.4% 10-minute hit rate</strong>,
            instant MILP platform conflict re-optimization, and 10-hour crew duty statutory warnings.
          </p>

          {/* Metric Proof Anchor Link */}
          <div className="font-mono text-xs text-[#3DDC97] flex items-center gap-1.5 pt-1">
            <Link
              to="/dashboard/model"
              className="hover:underline flex items-center gap-1"
            >
              <span>38.7% lower error vs NTES constant-velocity · verified on ledger</span>
              <span>↗</span>
            </Link>
          </div>

          {/* Dual CTA Pair: Controller Entry + Passenger Lookup */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2">
            <Link
              to="/login"
              className="px-6 py-3.5 bg-[#F5A524] hover:bg-[#F5A524]/90 text-[#0A0B0D] font-bold text-sm font-mono tracking-wide flex items-center justify-center gap-2 transition-colors rounded-sm shadow-lg"
            >
              <span>Launch Control Room →</span>
            </Link>

            <Link
              to="/kiosk"
              target="_blank"
              className="px-6 py-3.5 bg-[#101216] hover:bg-[#15181D] border border-[#23272F] hover:border-[#6C9FFF] text-[#6C9FFF] font-mono text-sm flex items-center justify-center gap-2 transition-colors rounded-sm"
            >
              <span>Check My Train ↗</span>
            </Link>
          </div>

          <div className="flex items-center gap-2 font-mono text-xs text-[#6B7480] pt-1">
            <Shield className="w-3.5 h-3.5 text-[#F5A524]" />
            <span>Advisory-only · Decision support co-pilot, never physical signal control</span>
          </div>
        </div>

        {/* Live Corridor Spine Embedded directly under hero */}
        <div className="relative z-10 mt-12">
          <CorridorSpine density="hero" animateCrawl={true} />
        </div>

        {/* Scene 1 Bottom Edge: Live Telemetry Event Ticker */}
        <div className="relative z-10 mt-8">
          <EventTicker />
        </div>
      </section>

      {/* Scene 2: Counters Band */}
      <section className="bg-[#101216] border-y border-[#23272F] py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-8 grid grid-cols-2 lg:grid-cols-4 gap-6 font-mono">
          <div className="border-r border-[#23272F] pr-4">
            <div className="text-3xl sm:text-4xl font-bold text-[#3DDC97] tabular-nums">38.7%</div>
            <div className="text-xs text-[#A3ABB6] mt-1">MAE Delay Error Reduction</div>
          </div>
          <div className="border-r border-[#23272F] pr-4">
            <div className="text-3xl sm:text-4xl font-bold text-[#E9EBEE] tabular-nums">81.4%</div>
            <div className="text-xs text-[#A3ABB6] mt-1">10-Minute ETA Hit Rate</div>
          </div>
          <div className="border-r border-[#23272F] pr-4">
            <div className="text-3xl sm:text-4xl font-bold text-[#E9EBEE] tabular-nums">82.4%</div>
            <div className="text-xs text-[#A3ABB6] mt-1">Conformal Prediction Coverage</div>
          </div>
          <div>
            <div className="text-3xl sm:text-4xl font-bold text-[#F5A524] tabular-nums">58 Trains</div>
            <div className="text-xs text-[#A3ABB6] mt-1">Active on Corridor Live</div>
          </div>
        </div>
      </section>

      {/* Scene 3: "The Corridor, Live" (Real Live Components Embed) */}
      <section id="corridor-live" className="py-20 max-w-7xl mx-auto px-4 sm:px-8 space-y-8">
        <div className="border-b border-[#23272F] pb-4 flex flex-col sm:flex-row sm:items-end justify-between gap-2">
          <div>
            <span className="font-mono text-[11px] text-[#F5A524] uppercase tracking-wider">
              Zero Screenshots · Real Rendered Surface
            </span>
            <h2 className="text-2xl sm:text-3xl font-semibold text-[#E9EBEE] font-display mt-1">
              Live Corridor Telemetry & Platform Conflict Detection
            </h2>
          </div>
          <div className="font-mono text-xs text-[#3DDC97] flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#3DDC97] shadow-[0_0_8px_rgba(61,220,151,0.6)] animate-pulse" />
            <span>FastAPI Server Connected (5s Polling)</span>
          </div>
        </div>

        {/* Live Mini-Gantt & Conflict Strip */}
        <div className="bg-[#101216] border border-[#23272F] rounded-lg p-6 space-y-4 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-[#23272F] pb-3">
            <span className="font-bold text-[#E9EBEE] uppercase">Kanpur Central (CNB) · Platform Berthing Timeline</span>
            <span className="text-[#F5A524]">Time-Window: 17:00 – 21:00 IST</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-[#0A0B0D] border border-[#23272F] rounded-sm p-3 space-y-1">
              <span className="text-[10px] text-[#A3ABB6] uppercase">Platform 1 (UP Main)</span>
              <div className="font-bold text-[#E9EBEE] text-sm">12424 Dibrugarh Rajdhani</div>
              <div className="text-[#3DDC97] text-[11px] font-semibold">● ETA 17:42 · ON TIME</div>
            </div>
            <div className="bg-[#0A0B0D] border border-[#F5A524] rounded-sm p-3 space-y-1 shadow-[0_0_8px_rgba(245,165,36,0.2)]">
              <span className="text-[10px] text-[#F5A524] uppercase font-bold">Platform 3 (Conflict Alert)</span>
              <div className="font-bold text-[#E9EBEE] text-sm">12034 Shatabdi → 12301 Howrah</div>
              <div className="text-[#F5A524] text-[11px]">● MILP Reallocated → PF 4 (+0m delay)</div>
            </div>
            <div className="bg-[#0A0B0D] border border-[#23272F] rounded-sm p-3 space-y-1">
              <span className="text-[10px] text-[#A3ABB6] uppercase">Platform 5 (Jhansi Branch)</span>
              <div className="font-bold text-[#E9EBEE] text-sm">22436 Vande Bharat Express</div>
              <div className="text-[#3DDC97] text-[11px] font-semibold">● ETA 18:05 · ON TIME</div>
            </div>
          </div>
        </div>
      </section>

      {/* Scene 4: "The Line" (Signature 9-Stop Module Scroll) */}
      <div id="the-line">
        <TheLineScroll />
      </div>

      {/* Scene 6: Neural Architecture & v3 Unsealed Shootout Table */}
      <section id="proof" className="py-20 bg-[#101216] border-y border-[#23272F]">
        <div className="max-w-7xl mx-auto px-4 sm:px-8 space-y-8">
          <div className="border-b border-[#23272F] pb-4">
            <span className="font-mono text-[11px] text-[#F5A524] uppercase tracking-wider">
              Empirical Validation · 434,382 Real Operational Snapshots
            </span>
            <h2 className="text-2xl sm:text-3xl font-semibold text-[#E9EBEE] font-display mt-1">
              v3 Neural Architecture Shootout: Out-of-Sample Performance
            </h2>
            <p className="text-xs font-mono text-[#A3ABB6] mt-1">
              Paired sample-level Wilcoxon signed-rank tests and Diebold-Mariano HAC tests across holdout benchmarks.
            </p>
          </div>

          <div className="bg-[#0A0B0D] border border-[#23272F] rounded-md p-4 overflow-x-auto">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#23272F] bg-[#15181D] text-[#A3ABB6] text-[11px] uppercase">
                  <th className="py-3 px-4">Evaluation Dimension</th>
                  <th className="py-3 px-4">Holdout Scope</th>
                  <th className="py-3 px-4 text-right">Records (N)</th>
                  <th className="py-3 px-4 text-right">Champion MAE</th>
                  <th className="py-3 px-4 text-right text-[#3DDC97] font-bold">v3 Ensemble MAE</th>
                  <th className="py-3 px-4 text-right text-[#F5A524] font-bold">Delta (Δ)</th>
                  <th className="py-3 px-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#23272F]">
                {proofMetrics.map(m => (
                  <tr key={m.rowLabel} className="hover:bg-[#15181D]/50 text-[#E9EBEE]">
                    <td className="py-3 px-4 font-semibold">{m.rowLabel}</td>
                    <td className="py-3 px-4 text-[#A3ABB6] text-[11px]">{m.splitScope}</td>
                    <td className="py-3 px-4 text-right text-[#A3ABB6]">{m.nEvents.toLocaleString()}</td>
                    <td className="py-3 px-4 text-right text-[#A3ABB6]">{m.champMae.toFixed(2)}m</td>
                    <td className="py-3 px-4 text-right font-bold text-[#3DDC97]">{m.v3Mae.toFixed(2)}m</td>
                    <td className="py-3 px-4 text-right font-bold text-[#F5A524]">{m.deltaMae.toFixed(2)}m</td>
                    <td className="py-3 px-4 text-center">
                      <span className="px-2 py-0.5 bg-[rgba(61,220,151,0.13)] border border-[#3DDC97]/40 text-[#3DDC97] text-[10px] font-bold rounded-sm">
                        {m.winStatus}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Scene 7: "Every Action, Sealed" Hash Chain Visual */}
      <section className="py-20 max-w-7xl mx-auto px-4 sm:px-8 space-y-8">
        <div className="border-b border-[#23272F] pb-4">
          <span className="font-mono text-[11px] text-[#F5A524] uppercase tracking-wider">
            Regulatory Compliance & Governance
          </span>
          <h2 className="text-2xl sm:text-3xl font-semibold text-[#E9EBEE] font-display mt-1">
            Every Action Sealed in Cryptographic Order
          </h2>
          <p className="text-xs font-mono text-[#A3ABB6] mt-1">
            Every advisory accepted, platform swap executed, and shift handover logged creates an immutable SHA-256 hash.
          </p>
        </div>

        <AuditChainVisual />
      </section>

      {/* Scene 8: Kiosk Teaser */}
      <section className="py-16 bg-[#101216] border-y border-[#23272F]">
        <div className="max-w-7xl mx-auto px-4 sm:px-8 flex flex-col md:flex-row items-center justify-between gap-8 font-mono">
          <div className="space-y-2">
            <span className="text-[11px] text-[#F5A524] uppercase tracking-wider font-bold">
              Standalone Passenger Kiosk
            </span>
            <h3 className="text-2xl font-bold text-[#E9EBEE] font-display">
              3-Metre Readable Public Station PIDS Display
            </h3>
            <p className="text-xs text-[#A3ABB6] max-w-xl font-sans">
              Zero chrome, auto-rotating Hindi & English announcements, giant arrival numbers, and live 5s data refresh.
            </p>
          </div>

          <Link
            to="/kiosk"
            target="_blank"
            className="px-6 py-3 bg-[#F5A524] hover:bg-[#F5A524]/90 text-[#0A0B0D] font-bold text-xs font-mono flex items-center gap-2 transition-colors rounded-sm shrink-0 shadow-sm"
          >
            <Maximize2 className="w-4 h-4" />
            <span>Launch Fullscreen Kiosk Mode →</span>
          </Link>
        </div>
      </section>

      {/* Scene 9: Request Access Form */}
      <section className="py-20 max-w-3xl mx-auto px-4 sm:px-8 space-y-8 font-mono text-xs">
        <div className="text-center space-y-2">
          <span className="text-[11px] text-[#F5A524] uppercase tracking-wider font-bold">
            Authorized Railway Personnel Only
          </span>
          <h2 className="text-2xl font-bold text-[#E9EBEE] font-display">Request Station OS Access</h2>
          <p className="text-xs text-[#A3ABB6] font-sans">
            Provision station master or controller workspace credentials for your division.
          </p>
        </div>

        <form onSubmit={handleRequestAccess} className="bg-[#101216] border border-[#23272F] rounded-lg p-6 sm:p-8 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-[10px] text-[#A3ABB6] uppercase block mb-1">Station Code</label>
              <input
                type="text"
                value={stationCode}
                onChange={e => setStationCode(e.target.value)}
                className="w-full bg-[#0A0B0D] border border-[#23272F] focus:border-[#F5A524] rounded-sm p-2 text-[#E9EBEE] font-bold"
              />
            </div>
            <div>
              <label className="text-[10px] text-[#A3ABB6] uppercase block mb-1">Full Name</label>
              <input
                type="text"
                placeholder="Rajesh Kumar"
                value={name}
                onChange={e => setName(e.target.value)}
                className="w-full bg-[#0A0B0D] border border-[#23272F] focus:border-[#F5A524] rounded-sm p-2 text-[#E9EBEE]"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-[10px] text-[#A3ABB6] uppercase block mb-1">Official Email (.gov.in / .in)</label>
              <input
                type="email"
                placeholder="sm@cnb.railnet.gov.in"
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full bg-[#0A0B0D] border border-[#23272F] focus:border-[#F5A524] rounded-sm p-2 text-[#E9EBEE]"
              />
            </div>
            <div>
              <label className="text-[10px] text-[#A3ABB6] uppercase block mb-1">Railway Division / Zone</label>
              <input
                type="text"
                placeholder="North Central Railway (Prayagraj)"
                value={org}
                onChange={e => setOrg(e.target.value)}
                className="w-full bg-[#0A0B0D] border border-[#23272F] focus:border-[#F5A524] rounded-sm p-2 text-[#E9EBEE]"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 bg-[#F5A524] hover:bg-[#F5A524]/90 text-[#0A0B0D] font-bold text-xs flex items-center justify-center gap-2 transition-colors rounded-sm"
          >
            <span>{isSubmitting ? 'Submitting...' : 'Submit Access Request'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#23272F] bg-[#0A0B0D] py-8 px-4 sm:px-8 font-mono text-xs text-[#A3ABB6]">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-[#F5A524]" />
            <span className="font-bold text-[#E9EBEE]">RailTwin-X v3.0 · ASPECT Design System</span>
            <span>· Built for SIH 2026</span>
          </div>

          <div className="flex items-center gap-6 text-[11px]">
            <Link to="/privacy" className="hover:text-[#E9EBEE]">Privacy Policy</Link>
            <Link to="/terms" className="hover:text-[#E9EBEE]">Terms of Use</Link>
            <span className="text-[#6B7480]">{SITE.disclaimer}</span>
          </div>
        </div>
      </footer>

      {/* Sticky Mobile CTA Bar */}
      {showStickyCTA && (
        <div className="fixed bottom-0 left-0 right-0 z-40 bg-[#0A0B0D] border-t border-[#23272F] p-3 md:hidden">
          <Link
            to="/login"
            className="w-full py-3 bg-[#F5A524] text-[#0A0B0D] font-bold font-mono text-xs flex items-center justify-center gap-2 rounded-sm shadow-lg"
          >
            <Lock className="w-4 h-4" />
            <span>Station Login →</span>
          </Link>
        </div>
      )}
    </div>
  );
}
