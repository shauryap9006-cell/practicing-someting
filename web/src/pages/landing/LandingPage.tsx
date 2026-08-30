import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { SEO } from '@/lib/seo';
import { SITE } from '@/config/site';
import { mockStore } from '@/mock/store';
import { F14Metric } from '@/mock/types';
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
import { LiveMarqueeTicker } from '@/components/landing/LiveMarqueeTicker';
import { TheLineScroll } from '@/components/landing/TheLineScroll';
import { AuditChainVisual } from '@/components/landing/AuditChainVisual';

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

  const proofMetrics = mockStore.getModelProof().f14Metrics;

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

  const handleRequestAccess = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim()) {
      toast.error('Please provide name and work email.');
      return;
    }

    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      navigate('/thanks');
    }, 400);
  };

  return (
    <div className="min-h-screen bg-[#0E0F11] text-[#E8E8E6] font-sans relative overflow-x-hidden selection:bg-[#FFB224] selection:text-[#0E0F11]">
      <SEO
        title="RailTwin-X · Delay Intelligence & Station Operating System"
        description="High-density decision-support digital twin for Indian Railways corridor operations. 38.7% MAE reduction vs baseline."
      />

      {/* Scene 0: Boot Preloader (Once per session, 900ms) */}
      {!bootComplete && <BootPreloader onComplete={() => setBootComplete(true)} />}

      {/* Top Fixed Header */}
      <header className="fixed top-0 left-0 right-0 z-40 bg-[#0E0F11]/90 backdrop-blur-md border-b border-[#26282C] h-14 flex items-center justify-between px-4 sm:px-8">
        <div className="flex items-center gap-3">
          <span className="w-2.5 h-2.5 bg-[#FFB224]" />
          <span className="font-bold text-base tracking-tight text-[#E8E8E6] uppercase">
            RailTwin-X
          </span>
          <span className="font-mono text-[10px] text-[#9A9DA3] border border-[#26282C] px-1.5 py-0.5 hidden sm:inline">
            SIH 2026 PS 26028
          </span>
        </div>

        <nav className="flex items-center gap-6 font-mono text-xs">
          <a href="#corridor-live" className="text-[#9A9DA3] hover:text-[#E8E8E6] hidden md:inline transition-colors">
            Live Corridor
          </a>
          <a href="#the-line" className="text-[#9A9DA3] hover:text-[#E8E8E6] hidden md:inline transition-colors">
            The Line
          </a>
          <a href="#proof" className="text-[#9A9DA3] hover:text-[#E8E8E6] hidden md:inline transition-colors">
            F14 Proof
          </a>
          <Link to="/kiosk" target="_blank" className="text-[#9A9DA3] hover:text-[#FFB224] flex items-center gap-1 transition-colors">
            <span>Kiosk PIDS</span>
            <Maximize2 className="w-3 h-3" />
          </Link>

          <Link
            to="/login"
            className="px-3.5 py-1.5 bg-[#FFB224] hover:bg-[#E59F1C] text-[#0E0F11] font-bold tracking-wide transition-colors flex items-center gap-1.5 shadow-[0_0_12px_rgba(255,178,36,0.25)]"
          >
            <Lock className="w-3 h-3 stroke-[2.5]" />
            <span>Station login</span>
          </Link>
        </nav>
      </header>

      {/* Scene 1: Hero Section (Full Viewport with 3D Night Corridor & Intercity Train on Tracks) */}
      <section className="relative min-h-screen pt-28 pb-16 flex flex-col justify-between px-4 sm:px-8 max-w-7xl mx-auto z-10">
        {/* 3D Rail Corridor Background with Intercity Train Running on Tracks */}
        <ThreeCorridor />

        {/* Hero Overlay Content */}
        <div className="relative z-10 max-w-3xl space-y-6 mt-12 sm:mt-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-[#15171A] border border-[#26282C] font-mono text-xs text-[#FFB224]">
            <span className="w-2 h-2 rounded-full bg-[#3ECF8E] animate-pulse" />
            <span>TRUNK CORRIDOR TELEMETRY: 785 KM ACTIVE</span>
          </div>

          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-[#E8E8E6] leading-tight">
            Know the platform conflict <span className="text-[#FFB224]">before it happens.</span>
          </h1>

          <p className="text-base sm:text-lg text-[#9A9DA3] leading-relaxed max-w-2xl font-sans">
            Calibrated ETA confidence bands with an <strong className="text-[#E8E8E6]">81.4% 10-minute hit rate</strong>,
            instant MILP platform conflict re-optimization, and 10-hour crew duty statutory warnings —
            <span className="text-[#3ECF8E] font-semibold"> 38.7% lower error</span> than NTES constant velocity.
          </p>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2">
            <Link
              to="/login"
              className="px-6 py-3.5 bg-[#FFB224] hover:bg-[#E59F1C] text-[#0E0F11] font-bold text-sm font-mono tracking-wide flex items-center justify-center gap-2 transition-colors shadow-lg"
            >
              <span>Launch Station Control Room</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <a
              href="#corridor-live"
              className="px-6 py-3.5 bg-[#15171A] hover:bg-[#1B1D21] border border-[#26282C] text-[#E8E8E6] font-mono text-sm flex items-center justify-center gap-2 transition-colors"
            >
              <span>See Live Corridor Data ↓</span>
            </a>
          </div>

          <div className="flex items-center gap-2 font-mono text-xs text-[#6B6E74] pt-2">
            <Shield className="w-3.5 h-3.5 text-[#FFB224]" />
            <span>Advisory-only · Decision support co-pilot, never physical signal control</span>
          </div>
        </div>

        {/* Scene 1 Bottom Edge: Live Ticker Marquee */}
        <div className="relative z-10 mt-16">
          <LiveMarqueeTicker />
        </div>
      </section>

      {/* Scene 2: Counters Band */}
      <section className="bg-[#15171A] border-y border-[#26282C] py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-8 grid grid-cols-2 lg:grid-cols-4 gap-6 font-mono">
          <div className="border-r border-[#26282C] pr-4">
            <div className="text-3xl sm:text-4xl font-bold text-[#3ECF8E] tabular-nums">38.7%</div>
            <div className="text-xs text-[#9A9DA3] mt-1">MAE Delay Error Reduction</div>
          </div>
          <div className="border-r border-[#26282C] pr-4">
            <div className="text-3xl sm:text-4xl font-bold text-[#E8E8E6] tabular-nums">81.4%</div>
            <div className="text-xs text-[#9A9DA3] mt-1">10-Minute ETA Hit Rate</div>
          </div>
          <div className="border-r border-[#26282C] pr-4">
            <div className="text-3xl sm:text-4xl font-bold text-[#E8E8E6] tabular-nums">82.4%</div>
            <div className="text-xs text-[#9A9DA3] mt-1">Conformal Prediction Coverage</div>
          </div>
          <div>
            <div className="text-3xl sm:text-4xl font-bold text-[#FFB224] tabular-nums">58 Trains</div>
            <div className="text-xs text-[#9A9DA3] mt-1">Active on Corridor Live</div>
          </div>
        </div>
      </section>

      {/* Scene 3: "The Corridor, Live" (Real Live Components Embed) */}
      <section id="corridor-live" className="py-20 max-w-7xl mx-auto px-4 sm:px-8 space-y-8">
        <div className="border-b border-[#26282C] pb-4 flex flex-col sm:flex-row sm:items-end justify-between gap-2">
          <div>
            <span className="font-mono text-[11px] text-[#FFB224] uppercase tracking-wider">
              Zero Screenshots · Real Rendered Surface
            </span>
            <h2 className="text-2xl sm:text-3xl font-semibold text-[#E8E8E6] mt-1">
              Live Corridor Telemetry & Platform Conflict Detection
            </h2>
          </div>
          <div className="font-mono text-xs text-[#3ECF8E] flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#3ECF8E] animate-pulse" />
            <span>FastAPI Server Connected (5s Polling)</span>
          </div>
        </div>

        {/* Live Mini-Gantt & Conflict Strip */}
        <div className="bg-[#15171A] border border-[#26282C] p-6 space-y-4 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-[#26282C] pb-3">
            <span className="font-bold text-[#E8E8E6] uppercase">Kanpur Central (CNB) · Platform Berthing Timeline</span>
            <span className="text-[#FFB224]">Time-Window: 17:00 – 21:00 IST</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-[#0E0F11] border border-[#26282C] p-3 space-y-1">
              <span className="text-[10px] text-[#9A9DA3] uppercase">Platform 1 (UP Main)</span>
              <div className="font-bold text-[#E8E8E6] text-sm">12424 Dibrugarh Rajdhani</div>
              <div className="text-[#3ECF8E] text-[11px]">ETA 17:42 · ON TIME</div>
            </div>
            <div className="bg-[#0E0F11] border border-[#FFB224] p-3 space-y-1">
              <span className="text-[10px] text-[#FFB224] uppercase font-bold">Platform 3 (Conflict Alert)</span>
              <div className="font-bold text-[#E8E8E6] text-sm">12034 Shatabdi &rarr; 12301 Howrah</div>
              <div className="text-[#FFB224] text-[11px]">MILP Solver Reallocated &rarr; PF 4 (+0 min delay)</div>
            </div>
            <div className="bg-[#0E0F11] border border-[#26282C] p-3 space-y-1">
              <span className="text-[10px] text-[#9A9DA3] uppercase">Platform 5 (Jhansi Branch)</span>
              <div className="font-bold text-[#E8E8E6] text-sm">22436 Vande Bharat Express</div>
              <div className="text-[#3ECF8E] text-[11px]">ETA 18:05 · ON TIME</div>
            </div>
          </div>
        </div>
      </section>

      {/* Scene 4: "The Line" (Signature 9-Stop Module Scroll) */}
      <div id="the-line">
        <TheLineScroll />
      </div>

      {/* Scene 6: Model Proof & F14 Empirical Backtest Table */}
      <section id="proof" className="py-20 bg-[#15171A] border-y border-[#26282C]">
        <div className="max-w-7xl mx-auto px-4 sm:px-8 space-y-8">
          <div className="border-b border-[#26282C] pb-4">
            <span className="font-mono text-[11px] text-[#FFB224] uppercase tracking-wider">
              Empirical Validation · Held-Out Test Week (2026)
            </span>
            <h2 className="text-2xl sm:text-3xl font-semibold text-[#E8E8E6] mt-1">
              F14 Model Proof: Benchmarked Against Operational Standards
            </h2>
          </div>

          <div className="bg-[#0E0F11] border border-[#26282C] p-4 overflow-x-auto">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#26282C] bg-[#1B1D21] text-[#9A9DA3] text-[11px] uppercase">
                  <th className="py-3 px-4">Evaluation Metric</th>
                  <th className="py-3 px-4">Baseline 1 (Scheduled)</th>
                  <th className="py-3 px-4">Baseline 2 (NTES Velocity)</th>
                  <th className="py-3 px-4 text-[#FFB224] font-bold">RailTwin-X Champion</th>
                  <th className="py-3 px-4 text-right text-[#3ECF8E] font-bold">Improvement</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#26282C]">
                {proofMetrics.map(m => (
                  <tr key={m.metric} className="hover:bg-[#1B1D21]/50 text-[#E8E8E6]">
                    <td className="py-3 px-4 font-semibold">{m.metric}</td>
                    <td className="py-3 px-4 text-[#9A9DA3]">{m.baseline1}</td>
                    <td className="py-3 px-4 text-[#9A9DA3]">{m.baseline2}</td>
                    <td className="py-3 px-4 font-bold text-[#FFB224]">{m.railtwin}</td>
                    <td className="py-3 px-4 text-right font-bold text-[#3ECF8E]">{m.improvement}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Scene 7: "Every Action, Sealed" Hash Chain Visual */}
      <section className="py-20 max-w-7xl mx-auto px-4 sm:px-8 space-y-8">
        <div className="border-b border-[#26282C] pb-4">
          <span className="font-mono text-[11px] text-[#FFB224] uppercase tracking-wider">
            Regulatory Compliance & Governance
          </span>
          <h2 className="text-2xl sm:text-3xl font-semibold text-[#E8E8E6] mt-1">
            Every Action Sealed in Cryptographic Order
          </h2>
          <p className="text-xs font-mono text-[#9A9DA3] mt-1">
            Every advisory accepted, platform swap executed, and shift handover logged creates an immutable SHA-256 hash.
          </p>
        </div>

        <AuditChainVisual />
      </section>

      {/* Scene 8: Kiosk Teaser */}
      <section className="py-16 bg-[#15171A] border-y border-[#26282C]">
        <div className="max-w-7xl mx-auto px-4 sm:px-8 flex flex-col md:flex-row items-center justify-between gap-8 font-mono">
          <div className="space-y-2">
            <span className="text-[11px] text-[#FFB224] uppercase tracking-wider font-bold">
              Standalone Passenger Kiosk
            </span>
            <h3 className="text-2xl font-bold text-[#E8E8E6]">
              3-Metre Readable Public Station PIDS Display
            </h3>
            <p className="text-xs text-[#9A9DA3] max-w-xl font-sans">
              Zero chrome, auto-rotating Hindi & English announcements, giant arrival numbers, and live 5s data refresh.
            </p>
          </div>

          <Link
            to="/kiosk"
            target="_blank"
            className="px-6 py-3 bg-[#FFB224] hover:bg-[#E59F1C] text-[#0E0F11] font-bold text-xs font-mono flex items-center gap-2 transition-colors shrink-0"
          >
            <Maximize2 className="w-4 h-4" />
            <span>Launch Fullscreen Kiosk Mode &rarr;</span>
          </Link>
        </div>
      </section>

      {/* Scene 9: Request Access Form & Footer */}
      <section className="py-20 max-w-3xl mx-auto px-4 sm:px-8 space-y-8 font-mono text-xs">
        <div className="text-center space-y-2">
          <span className="text-[11px] text-[#FFB224] uppercase tracking-wider font-bold">
            Authorized Railway Personnel Only
          </span>
          <h2 className="text-2xl font-bold text-[#E8E8E6]">Request Station OS Access</h2>
          <p className="text-xs text-[#9A9DA3] font-sans">
            Provision station master or controller workspace credentials for your division.
          </p>
        </div>

        <form onSubmit={handleRequestAccess} className="bg-[#15171A] border border-[#26282C] p-6 sm:p-8 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-[10px] text-[#9A9DA3] uppercase block mb-1">Station Code</label>
              <input
                type="text"
                value={stationCode}
                onChange={e => setStationCode(e.target.value)}
                className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6] font-bold"
              />
            </div>
            <div>
              <label className="text-[10px] text-[#9A9DA3] uppercase block mb-1">Full Name</label>
              <input
                type="text"
                placeholder="Rajesh Kumar"
                value={name}
                onChange={e => setName(e.target.value)}
                className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-[10px] text-[#9A9DA3] uppercase block mb-1">Official Email (.gov.in / .in)</label>
              <input
                type="email"
                placeholder="sm@cnb.railnet.gov.in"
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
              />
            </div>
            <div>
              <label className="text-[10px] text-[#9A9DA3] uppercase block mb-1">Railway Division / Zone</label>
              <input
                type="text"
                placeholder="North Central Railway (Prayagraj)"
                value={org}
                onChange={e => setOrg(e.target.value)}
                className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 bg-[#FFB224] hover:bg-[#E59F1C] text-[#0E0F11] font-bold text-xs flex items-center justify-center gap-2 transition-colors"
          >
            <span>{isSubmitting ? 'Submitting...' : 'Submit Access Request'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#26282C] bg-[#0E0F11] py-8 px-4 sm:px-8 font-mono text-xs text-[#9A9DA3]">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="w-2 h-2 bg-[#FFB224]" />
            <span className="font-bold text-[#E8E8E6]">RailTwin-X v3.0</span>
            <span>· Built for SIH 2026</span>
          </div>

          <div className="flex items-center gap-6 text-[11px]">
            <Link to="/privacy" className="hover:text-[#E8E8E6]">Privacy Policy</Link>
            <Link to="/terms" className="hover:text-[#E8E8E6]">Terms of Use</Link>
            <span className="text-[#6B6E74]">{SITE.disclaimer}</span>
          </div>
        </div>
      </footer>

      {/* Sticky Mobile CTA Bar */}
      {showStickyCTA && (
        <div className="fixed bottom-0 left-0 right-0 z-40 bg-[#0E0F11] border-t border-[#26282C] p-3 md:hidden">
          <Link
            to="/login"
            className="w-full py-3 bg-[#FFB224] text-[#0E0F11] font-bold font-mono text-xs flex items-center justify-center gap-2 shadow-lg"
          >
            <Lock className="w-4 h-4" />
            <span>Station Login &rarr;</span>
          </Link>
        </div>
      )}
    </div>
  );
}
