import React, { Suspense, lazy, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const ThreeCorridor = lazy(() =>
  import('./ThreeCorridor').then((m) => ({ default: m.ThreeCorridor }))
);

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [quickTrainNo, setQuickTrainNo] = useState('');

  const handleQuickTrack = (e: React.FormEvent) => {
    e.preventDefault();
    if (quickTrainNo.trim()) {
      navigate(`/t/${quickTrainNo.trim()}`);
    } else {
      navigate('/t');
    }
  };

  return (
    <div className="relative min-h-screen bg-[#050505] text-[#F3EFE6] overflow-x-hidden select-none flex flex-col justify-between">
      {/* 3D Canvas Background: Preserved Mountain, Train & Procedural Grass Field */}
      <Suspense
        fallback={
          <div className="absolute inset-0 bg-[#050505] flex items-center justify-center pointer-events-none">
            <div className="w-8 h-8 rounded-full border-2 border-[#38332A] border-t-[#E6A100] animate-spin" />
          </div>
        }
      >
        <ThreeCorridor />
      </Suspense>

      {/* Top Navigation Bar Overlay */}
      <header className="relative z-20 px-6 py-5 flex items-center justify-between max-w-7xl mx-auto w-full">
        <Link to="/" className="flex flex-col gap-0.5 group">
          <span className="font-serif text-xl font-bold tracking-tight text-[#FDFCF8] group-hover:text-[#E6A100] transition-colors">
            RAILTWIN-X
          </span>
          <span className="font-mono text-[9px] uppercase tracking-widest text-[#A8A194]">
            SIH PS 26028 · The Working Timetable
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-6 font-mono text-xs text-[#A8A194]">
          <Link to="/t" className="hover:text-[#FDFCF8] transition-colors">
            Tracker
          </Link>
          <Link to="/network" className="hover:text-[#FDFCF8] transition-colors">
            Corridor Twin
          </Link>
          <Link to="/compare" className="hover:text-[#FDFCF8] transition-colors">
            Shock Lab
          </Link>
          <Link to="/proof" className="hover:text-[#FDFCF8] transition-colors">
            Model Proof
          </Link>
          <Link to="/kiosk" className="hover:text-[#FDFCF8] transition-colors">
            Station PIDS
          </Link>
          <Link
            to="/t"
            className="px-3 py-1.5 bg-[#FDFCF8] text-[#191712] font-semibold rounded-[3px] hover:bg-[#E6A100] transition-colors"
          >
            Launch Twin →
          </Link>
        </nav>
      </header>

      {/* Hero Body Content Overlay */}
      <main className="relative z-20 max-w-5xl mx-auto px-6 py-12 sm:py-20 flex flex-col gap-8 text-left">
        <div className="flex flex-col gap-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-[3px] bg-[#1C1A14]/80 border border-[#38332A] backdrop-blur-sm self-start">
            <span className="w-2 h-2 rounded-[2px] bg-[#E6A100] animate-pulse" />
            <span className="font-mono text-xs uppercase tracking-wider text-[#E6A100] font-semibold">
              Live Operational Twin · NDLS &mdash; HWH Main Trunk (1,447 km)
            </span>
          </div>

          <h1 className="font-serif text-4xl sm:text-6xl font-bold tracking-tight text-[#FDFCF8] leading-[1.1]">
            Dynamic ETA Forecasting &amp; Operational Twin for Indian Railways
          </h1>

          <p className="font-sans text-base sm:text-lg text-[#CDC5B4] max-w-2xl leading-relaxed">
            Replaces static frozen schedules with probabilistic arrival cones (P10–P90),
            100% additive root-cause delay attribution, and SHA-256 cryptographic audit receipts.
          </p>
        </div>

        {/* Quick Search / Track Box */}
        <form
          onSubmit={handleQuickTrack}
          className="flex flex-col sm:flex-row gap-2 max-w-xl bg-[#181612]/90 p-2 border border-[#38332A] rounded-[4px] backdrop-blur-sm"
        >
          <input
            type="text"
            value={quickTrainNo}
            onChange={(e) => setQuickTrainNo(e.target.value)}
            placeholder="Enter train number (e.g. 12301, 12004, 12424)..."
            className="flex-1 bg-transparent px-3 py-2.5 font-mono text-sm text-[#FDFCF8] placeholder:text-[#8A8477] focus:outline-none"
          />
          <button
            type="submit"
            className="px-5 py-2.5 bg-[#E6A100] text-[#191712] font-mono text-xs uppercase tracking-wider font-bold rounded-[3px] hover:bg-[#F2B01E] transition-colors cursor-pointer"
          >
            Track Train →
          </button>
        </form>

        {/* Direct Action Hub Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4">
          <Link
            to="/t"
            className="p-4 bg-[#181612]/80 border border-[#38332A] hover:border-[#E6A100] rounded-[4px] transition-colors flex flex-col gap-1.5 group"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs uppercase tracking-wider text-[#E6A100] font-semibold">
                SURFACE 01
              </span>
              <span className="text-xs text-[#A8A194] group-hover:translate-x-1 transition-transform">
                →
              </span>
            </div>
            <span className="font-serif text-lg font-bold text-[#FDFCF8]">
              Train Tracker
            </span>
            <span className="font-sans text-xs text-[#A8A194]">
              Arrival cone, why-late waterfall, and downstream transfer custody.
            </span>
          </Link>

          <Link
            to="/compare"
            className="p-4 bg-[#181612]/80 border border-[#38332A] hover:border-[#E6A100] rounded-[4px] transition-colors flex flex-col gap-1.5 group"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs uppercase tracking-wider text-[#E6A100] font-semibold">
                SURFACE 02
              </span>
              <span className="text-xs text-[#A8A194] group-hover:translate-x-1 transition-transform">
                →
              </span>
            </div>
            <span className="font-serif text-lg font-bold text-[#FDFCF8]">
              The Shock Lab
            </span>
            <span className="font-sans text-xs text-[#A8A194]">
              Inject signal failures and speed restrictions. Compare vs official NTES.
            </span>
          </Link>

          <Link
            to="/proof"
            className="p-4 bg-[#181612]/80 border border-[#38332A] hover:border-[#E6A100] rounded-[4px] transition-colors flex flex-col gap-1.5 group"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs uppercase tracking-wider text-[#E6A100] font-semibold">
                SURFACE 03
              </span>
              <span className="text-xs text-[#A8A194] group-hover:translate-x-1 transition-transform">
                →
              </span>
            </div>
            <span className="font-serif text-lg font-bold text-[#FDFCF8]">
              Cryptographic Proof
            </span>
            <span className="font-sans text-xs text-[#A8A194]">
              SHA-256 block receipts, out-of-sample error, and 80% empirical coverage.
            </span>
          </Link>
        </div>
      </main>

      {/* Bottom Footer Overlay */}
      <footer className="relative z-20 px-6 py-6 border-t border-[#38332A]/70 max-w-7xl mx-auto w-full flex flex-wrap items-center justify-between gap-4 font-mono text-xs text-[#8A8477]">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-[2px] bg-[#1B6B3A]" />
          <span>RailTwin-X v4 &middot; The Working Timetable</span>
        </div>

        <div className="flex items-center gap-4">
          <Link to="/network" className="hover:text-[#FDFCF8] transition-colors">
            1D Corridor Twin
          </Link>
          <Link to="/kiosk" className="hover:text-[#FDFCF8] transition-colors">
            Station PIDS Board
          </Link>
          <span>FastAPI :8000</span>
        </div>
      </footer>
    </div>
  );
};
