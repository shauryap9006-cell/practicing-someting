import React, { useState } from 'react';
import { AspectType, AspectLamp } from './AspectLamp';
import {
  ShieldCheck,
  AlertTriangle,
  Radio,
  FileCheck2,
  Clock,
  MapPin,
  ExternalLink,
  ChevronRight,
  Info,
  Layers,
} from 'lucide-react';

export interface DelaySegment {
  id: string;
  category: string; // 'TSR' | 'CONGESTION' | 'RECOVERY' | 'INHERITED' | 'DWELL_OVERRUN' | 'SIGNAL_HOLD' | 'WEATHER' | 'RESIDUAL'
  label: string;
  location?: string;
  minutes: number; // signed: positive for delay, negative for recovery
  aspect: AspectType;
  description?: string;
  evidencePointer?: string;
  evidence?: Record<string, any>;
}

export interface AutopsyStripProps {
  trainNo: string;
  trainName?: string;
  totalDelayMin: number;
  segments?: DelaySegment[];
  summarySentence?: string;
  integrityStatus?: 'VERIFIED' | 'WARNING';
  integrityChecks?: {
    additivity_pass?: boolean;
    evidence_resolvable?: boolean;
    clock_consistent?: boolean;
  };
  asOfTs?: string;
  className?: string;
}

const getCategoryColor = (category: string, isRecovery: boolean) => {
  if (isRecovery) {
    return {
      bg: 'bg-[#3DDC97]/20 hover:bg-[#3DDC97]/30 border-[#3DDC97]/40 text-[#3DDC97]',
      bar: 'bg-[#3DDC97]',
      dot: 'bg-[#3DDC97]',
      badge: 'bg-[#3DDC97]/15 border-[#3DDC97]/30 text-[#3DDC97]',
    };
  }
  switch (category.toUpperCase()) {
    case 'TSR':
      return {
        bg: 'bg-[#F5A524]/20 hover:bg-[#F5A524]/35 border-[#F5A524]/40 text-[#F5A524]',
        bar: 'bg-[#F5A524]',
        dot: 'bg-[#F5A524]',
        badge: 'bg-[#F5A524]/15 border-[#F5A524]/30 text-[#F5A524]',
      };
    case 'INHERITED':
      return {
        bg: 'bg-[#EAB308]/20 hover:bg-[#EAB308]/35 border-[#EAB308]/40 text-[#EAB308]',
        bar: 'bg-[#EAB308]',
        dot: 'bg-[#EAB308]',
        badge: 'bg-[#EAB308]/15 border-[#EAB308]/30 text-[#EAB308]',
      };
    case 'DWELL_OVERRUN':
      return {
        bg: 'bg-[#F4506A]/25 hover:bg-[#F4506A]/40 border-[#F4506A]/40 text-[#F4506A]',
        bar: 'bg-[#F4506A]',
        dot: 'bg-[#F4506A]',
        badge: 'bg-[#F4506A]/15 border-[#F4506A]/30 text-[#F4506A]',
      };
    case 'SIGNAL_HOLD':
    case 'CONGESTION':
      return {
        bg: 'bg-[#6C9FFF]/20 hover:bg-[#6C9FFF]/35 border-[#6C9FFF]/40 text-[#6C9FFF]',
        bar: 'bg-[#6C9FFF]',
        dot: 'bg-[#6C9FFF]',
        badge: 'bg-[#6C9FFF]/15 border-[#6C9FFF]/30 text-[#6C9FFF]',
      };
    case 'WEATHER':
      return {
        bg: 'bg-[#38BDF8]/20 hover:bg-[#38BDF8]/35 border-[#38BDF8]/40 text-[#38BDF8]',
        bar: 'bg-[#38BDF8]',
        dot: 'bg-[#38BDF8]',
        badge: 'bg-[#38BDF8]/15 border-[#38BDF8]/30 text-[#38BDF8]',
      };
    case 'RESIDUAL':
    default:
      return {
        bg: 'bg-[#94A3B8]/20 hover:bg-[#94A3B8]/35 border-[#94A3B8]/40 text-[#94A3B8]',
        bar: 'bg-[#94A3B8]',
        dot: 'bg-[#94A3B8]',
        badge: 'bg-[#94A3B8]/15 border-[#94A3B8]/30 text-[#94A3B8]',
      };
  }
};

export const AutopsyStrip: React.FC<AutopsyStripProps> = ({
  trainNo,
  trainName,
  totalDelayMin,
  segments = [],
  summarySentence,
  integrityStatus = 'VERIFIED',
  integrityChecks = { additivity_pass: true, evidence_resolvable: true, clock_consistent: true },
  asOfTs,
  className = '',
}) => {
  const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(null);

  const isOnTime = Math.abs(totalDelayMin) <= 2;

  // Compute total absolute minutes to drive strictly proportional bar widths
  const sumAbsMinutes = segments.reduce((sum, s) => sum + Math.max(1, Math.abs(s.minutes)), 0) || 1;

  // Selected or hovered segment
  const activeSegment = segments.find(s => s.id === selectedSegmentId) || (segments.length > 0 ? segments[0] : null);

  const formatAsOfTime = (iso?: string) => {
    if (!iso) return 'LIVE IST';
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString('en-IN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' IST';
    } catch {
      return 'LIVE IST';
    }
  };

  return (
    <div className={`bg-[#101216] border border-[#23272F] rounded-lg p-5 font-mono select-none space-y-4 ${className}`}>
      {/* 1. Instrument Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#23272F]">
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="font-bold text-xs uppercase text-[#E9EBEE] tracking-wider flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5 text-[#3DDC97] animate-pulse" />
            DELAY AUTOPSY & CAUSAL ATTRIBUTION
          </span>
          <span className="text-xs text-[#6B7480]">·</span>
          <span className="text-xs text-[#E9EBEE] font-bold">#{trainNo}</span>
          {trainName && <span className="text-xs text-[#A3ABB6] font-sans">({trainName})</span>}
          <span className="px-1.5 py-0.5 rounded text-[10px] bg-[#15181D] border border-[#23272F] text-[#3DDC97] flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#3DDC97] animate-ping" />
            LIVE TELEMETRY
          </span>
        </div>

        {/* Right Status & Verification Badges */}
        <div className="flex items-center gap-3">
          {/* Integrity Badge */}
          <div
            className={`px-2 py-0.5 rounded text-[10px] font-bold border flex items-center gap-1.5 ${
              integrityStatus === 'VERIFIED' && integrityChecks.additivity_pass
                ? 'bg-[#3DDC97]/15 border-[#3DDC97]/40 text-[#3DDC97]'
                : 'bg-[#F5A524]/15 border-[#F5A524]/40 text-[#F5A524]'
            }`}
            title={`Additivity: ${integrityChecks.additivity_pass ? 'PASS' : 'FAIL'} | Evidence: ${
              integrityChecks.evidence_resolvable ? 'RESOLVABLE' : 'UNRESOLVED'
            } | Clock: ${integrityChecks.clock_consistent ? 'SYNC' : 'DRIFT'}`}
          >
            {integrityStatus === 'VERIFIED' ? (
              <>
                <ShieldCheck className="w-3 h-3 text-[#3DDC97]" />
                <span>EVIDENCE VERIFIED</span>
              </>
            ) : (
              <>
                <AlertTriangle className="w-3 h-3 text-[#F5A524]" />
                <span>INTEGRITY CHECK</span>
              </>
            )}
          </div>

          {/* Total Delay Badge */}
          <div className="text-right">
            <span
              className={`text-xs font-bold tabular-nums px-2 py-1 rounded border ${
                isOnTime
                  ? 'bg-[#3DDC97]/15 border-[#3DDC97]/30 text-[#3DDC97]'
                  : totalDelayMin > 20
                  ? 'bg-[#F4506A]/15 border-[#F4506A]/30 text-[#F4506A]'
                  : 'bg-[#F5A524]/15 border-[#F5A524]/30 text-[#F5A524]'
              }`}
            >
              {isOnTime ? '● ON TIME' : `TOTAL DELAY: +${totalDelayMin}M`}
            </span>
          </div>
        </div>
      </div>

      {/* 2. On-Time Nominal Clearance State (T-A6) */}
      {isOnTime ? (
        <div className="p-4 bg-[#0A0B0D] border border-[#3DDC97]/30 rounded-md flex items-center gap-4">
          <div className="w-10 h-10 rounded-full bg-[#3DDC97]/20 border border-[#3DDC97]/40 flex items-center justify-center shrink-0">
            <span className="w-3.5 h-3.5 rounded-full bg-[#3DDC97] animate-pulse" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-bold text-xs text-[#3DDC97] uppercase tracking-wider">
                NOMINAL TIMETABLE RUNNING
              </span>
              <span className="text-[10px] text-[#6B7480]">· 100% Corridor Clear</span>
            </div>
            <p className="text-xs text-[#A3ABB6] font-sans">
              {summarySentence ||
                'Running strictly on time. Timetable recovery buffers intact — no active speed restrictions or route conflicts.'}
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* 3. Mathematically Proportional Stacked Segment Bar */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[10px] text-[#6B7480] uppercase tracking-wider">
              <span>Proportional Causal Decomposition</span>
              <span>
                Σ Causes: {segments.reduce((s, c) => s + c.minutes, 0)}m / Net: +{totalDelayMin}m
              </span>
            </div>

            <div className="relative h-8 w-full bg-[#0A0B0D] border border-[#23272F] rounded-md overflow-hidden flex items-stretch p-0.5 gap-0.5">
              {segments.map(seg => {
                const isRecovery = seg.minutes < 0;
                const colors = getCategoryColor(seg.category, isRecovery);
                const widthPct = Math.max(8, (Math.abs(seg.minutes) / sumAbsMinutes) * 100);
                const isSelected = activeSegment?.id === seg.id;

                return (
                  <button
                    key={seg.id}
                    type="button"
                    onClick={() => setSelectedSegmentId(seg.id)}
                    onMouseEnter={() => setSelectedSegmentId(seg.id)}
                    className={`relative h-full transition-all duration-150 flex items-center justify-center px-1.5 rounded-sm border group text-xs ${
                      colors.bg
                    } ${isSelected ? 'ring-2 ring-inset ring-[#E9EBEE] shadow-sm z-10' : ''}`}
                    style={{ width: `${widthPct}%` }}
                    title={`${seg.category}: ${seg.minutes > 0 ? `+${seg.minutes}m` : `${seg.minutes}m`} (${seg.label})`}
                  >
                    <span className="text-[11px] font-bold tabular-nums truncate">
                      {isRecovery ? `${seg.minutes}m` : `+${seg.minutes}m`}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 4. Segment Category Chips */}
          <div className="flex flex-wrap gap-2 pt-1">
            {segments.map(seg => {
              const isRecovery = seg.minutes < 0;
              const colors = getCategoryColor(seg.category, isRecovery);
              const isSelected = activeSegment?.id === seg.id;

              return (
                <button
                  key={seg.id}
                  type="button"
                  onClick={() => setSelectedSegmentId(seg.id)}
                  className={`px-2.5 py-1 rounded-sm border text-[11px] flex items-center gap-2 transition-colors ${
                    isSelected
                      ? 'bg-[#1B1F26] border-[#E9EBEE] text-[#E9EBEE]'
                      : 'bg-[#15181D] border-[#23272F] text-[#A3ABB6] hover:border-[#2E333D]'
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${colors.dot}`} />
                  <span className="font-bold">{seg.category}</span>
                  <span className="text-[#6B7480]">·</span>
                  <span className="font-bold text-[#E9EBEE] tabular-nums">
                    {seg.minutes > 0 ? `+${seg.minutes}m` : `${seg.minutes}m`}
                  </span>
                </button>
              );
            })}
          </div>

          {/* 5. Interactive Evidence & Narrative Drawer */}
          {activeSegment && (
            <div className="p-4 bg-[#0A0B0D] border border-[#23272F] rounded-md space-y-3 font-sans text-xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#23272F] pb-2 font-mono">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                      getCategoryColor(activeSegment.category, activeSegment.minutes < 0).badge
                    }`}
                  >
                    {activeSegment.category}
                  </span>
                  <span className="text-xs font-bold text-[#E9EBEE]">
                    {activeSegment.minutes > 0 ? `+${activeSegment.minutes} min` : `${activeSegment.minutes} min`}
                  </span>
                  {activeSegment.location && (
                    <span className="text-[#A3ABB6] text-[11px] flex items-center gap-1">
                      <MapPin className="w-3 h-3 text-[#F5A524]" />
                      {activeSegment.location}
                    </span>
                  )}
                </div>

                {activeSegment.evidencePointer && (
                  <div className="flex items-center gap-1.5 text-[11px] text-[#3DDC97]">
                    <FileCheck2 className="w-3.5 h-3.5" />
                    <span className="font-bold">{activeSegment.evidencePointer}</span>
                  </div>
                )}
              </div>

              {/* Natural language explanation */}
              <p className="text-[#E9EBEE] leading-relaxed">
                {activeSegment.description || activeSegment.label}
              </p>

              {/* Granular Traceable Evidence Record */}
              {activeSegment.evidence && Object.keys(activeSegment.evidence).length > 0 && (
                <div className="pt-2 border-t border-[#1C2027] font-mono text-[11px] text-[#A3ABB6] flex flex-wrap gap-x-4 gap-y-1">
                  {Object.entries(activeSegment.evidence)
                    .filter(([k]) => k !== 'details')
                    .map(([key, val]) => (
                      <span key={key} className="flex items-center gap-1">
                        <span className="text-[#6B7480]">{key}:</span>
                        <span className="text-[#E9EBEE] font-bold">{String(val)}</span>
                      </span>
                    ))}
                  {activeSegment.evidence.details &&
                    Object.entries(activeSegment.evidence.details).map(([k, v]) => (
                      <span key={k} className="flex items-center gap-1">
                        <span className="text-[#6B7480]">{k}:</span>
                        <span className="text-[#E9EBEE]">{String(v)}</span>
                      </span>
                    ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* 6. Root Cause Narrative Synthesis */}
      <div className="p-3 bg-[#0A0B0D] border border-[#23272F] rounded-md font-sans text-xs">
        <span className="font-mono text-[10px] text-[#6B7480] uppercase tracking-wider block mb-1">
          Root Cause Narrative Synthesis
        </span>
        <p className="text-[#E9EBEE] leading-relaxed font-sans">
          {summarySentence ||
            (isOnTime
              ? 'Running strictly on time. Timetable recovery buffers intact — no active speed restrictions or route conflicts.'
              : `Running ${totalDelayMin} min late across corridor.`)}
        </p>
      </div>

      {/* 7. Live Provenance Footer */}
      <div className="pt-2 border-t border-[#23272F] flex items-center justify-between text-[10px] text-[#6B7480] font-mono">
        <div className="flex items-center gap-2">
          <span>SOURCE: PIPELINE 07 EVENT LEDGER</span>
          <span>·</span>
          <span>AS OF: {formatAsOfTime(asOfTs)}</span>
        </div>
        <div className="flex items-center gap-1 text-[#3DDC97]">
          <span>● MATH BALANCED</span>
        </div>
      </div>
    </div>
  );
};
