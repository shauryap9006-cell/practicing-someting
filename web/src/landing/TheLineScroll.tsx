import React, { useState } from 'react';
import { ArrowLeft, ArrowRight, Activity, Cpu, ShieldAlert, Users, Layers, Radio, FileText, CheckCircle2, Shield } from 'lucide-react';

interface StopItem {
  code: string;
  station: string;
  groupName: string;
  icon: React.ComponentType<{ className?: string }>;
  modules: string[];
  headline: string;
  previewType: string;
  previewData: Record<string, string>;
}

const STOPS: StopItem[] = [
  {
    code: 'NDLS',
    station: 'New Delhi',
    groupName: '1. Overview & Control Room',
    icon: Activity,
    modules: ['Live Station Board', 'Active Headway Counters', 'Priority Advisories Triage', 'Crew Duty Alert Watch'],
    headline: 'Single-screen situational clarity for the Station Master.',
    previewType: 'board',
    previewData: { title: 'CANVAS COUNTER STRIP', metric1: '58 Active Trains', metric2: '0 Conflicts', metric3: '3 Advisories' },
  },
  {
    code: 'GZB',
    station: 'Ghaziabad Jn',
    groupName: '2. Operations & Timetable',
    icon: Cpu,
    modules: ['Platform Gantt Scheduler', 'Timetable Version Diff', 'Block Section Line Clear', 'Shunting Moves Log'],
    headline: 'Sub-second conflict resolution & MILP re-optimization.',
    previewType: 'gantt',
    previewData: { title: 'CONFLICT RESOLUTION', sub: '12034 PF 3 ↔ 12301 PF 4', status: 'RESOLVED (+0 min delay)' },
  },
  {
    code: 'ALJN',
    station: 'Aligarh Jn',
    groupName: '3. Spatial & Yard Network',
    icon: Layers,
    modules: ['Corridor GIS Map (MapLibre)', 'Station Yard Micro-Track Layout', 'Signal Aspect State Tracker', 'Rooma/Juhi/Panki Sidings'],
    headline: 'Real track alignments and live signal aspect dots.',
    previewType: 'map',
    previewData: { title: 'YARD INTERLOCKING', track: 'UP MAIN · Aspect: GREEN', loops: 'Loop 1, 2, 3 OCCUPIED' },
  },
  {
    code: 'TDL',
    station: 'Tundla Jn',
    groupName: '4. Safety & Interlocking',
    icon: ShieldAlert,
    modules: ['TSR / Caution Order Registry', 'Incident & Near-Miss Log', 'Emergency SOP Checklist Runner', 'Level Crossing (LC) Monitor'],
    headline: 'Deterministic interlocking rules with automated escalation.',
    previewType: 'safety',
    previewData: { title: 'ACTIVE CAUTION ORDER', km: 'KM 1012.4 – 1018.6', limit: '30 km/h (Bridge Maint)' },
  },
  {
    code: 'ETW',
    station: 'Etawah Jn',
    groupName: '5. Crew & Workforce',
    icon: Users,
    modules: ['Crew Duty Breach Lookahead', 'Dynamic Rostering', 'Relief Dispatching', 'Sign-On / Sign-Off Tracking'],
    headline: '10-hour statutory duty cap enforcement with <2h warnings.',
    previewType: 'crew',
    previewData: { title: 'DUTY BREACH WATCH', lp: 'LP S. K. Verma (12034)', remaining: '1h 45m remaining (CRITICAL)' },
  },
  {
    code: 'CNB',
    station: 'Kanpur Central',
    groupName: '6. Infrastructure & Assets',
    icon: Layers,
    modules: ['Asset Registry & MTBF', 'Work Orders Kanban', 'Corridor Track-Block Gantt', 'Rake Cleaning & Turnaround'],
    headline: 'Predictive asset maintenance linked to track possessions.',
    previewType: 'kanban',
    previewData: { title: 'WORK ORDER KANBAN', card: 'Track Circuit 44 Sensitivity Calibration', due: 'Due Today · Er. Priya Patel' },
  },
  {
    code: 'PRYJ',
    station: 'Prayagraj Jn',
    groupName: '7. Section Coordination',
    icon: Radio,
    modules: ['Corridor Handoff Matrix', 'DFC Freight Precedence Controller', 'Preceding Loop Regulation', 'Inter-Division Handoffs'],
    headline: 'Corridor-wide precedence regulation between passenger & freight.',
    previewType: 'dfc',
    previewData: { title: 'DFC PRECEDENCE', freight: 'BOXN-7041 (Coal)', action: 'HOLD ON ROOMA DFC LOOP (-24m)' },
  },
  {
    code: 'MZP',
    station: 'Mirzapur',
    groupName: '8. Passenger & Commercial',
    icon: FileText,
    modules: ['Digital Delay Certificates (QR)', 'Multilingual PA Announcements', 'Stall Lease Tracker', 'Station PIDS Kiosk Screen'],
    headline: 'Cryptographically verified certificates and 3m-readable PIDS.',
    previewType: 'qr',
    previewData: { title: 'DELAY CERTIFICATE', cert: 'CERT-CNB-12034-884210', delay: '42 min delay · Signed NCR' },
  },
  {
    code: 'DDU',
    station: 'Pt. Deen Dayal Upadhyaya',
    groupName: '9. Governance & Integrity',
    icon: Shield,
    modules: ['Digital Shift Handover Logbook', 'SHA-256 Audit Hash Chain', 'RBAC User Management', 'Automated WAL DB Backups'],
    headline: 'Every operational decision cryptographically sealed in order.',
    previewType: 'audit',
    previewData: { title: 'HASH CHAIN INTEGRITY', status: 'VALID · 50 Entries Verified', hash: '0x8f2a11b9c402e9a781b0' },
  },
];

export function TheLineScroll() {
  const [activeIdx, setActiveIdx] = useState(0);

  const currentStop = STOPS[activeIdx];
  const Icon = currentStop.icon;

  return (
    <section className="py-20 bg-[#0E0F11] border-y border-[#26282C] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        {/* Section Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 pb-4 border-b border-[#26282C]">
          <div>
            <span className="font-mono text-[11px] uppercase tracking-wider text-[#FFB224]">
              Corridor Navigation · 26 Integrated Modules
            </span>
            <h2 className="text-2xl sm:text-3xl font-semibold text-[#E8E8E6] mt-1">
              The Line: 9 Stops Across The Digital Twin
            </h2>
          </div>
          <p className="font-mono text-xs text-[#9A9DA3] mt-2 md:mt-0">
            Stop {activeIdx + 1} of 9 · {currentStop.station} ({currentStop.code})
          </p>
        </div>

        {/* Rail Line Bar */}
        <div className="relative mb-8 pt-4">
          {/* Horizontal Track Line */}
          <div className="absolute top-1/2 left-0 right-0 h-1 bg-[#1B1D21] -translate-y-1/2 z-0">
            <div
              className="h-full bg-[#FFB224] transition-all duration-300"
              style={{ width: `${((activeIdx + 1) / STOPS.length) * 100}%` }}
            />
          </div>

          {/* Station Stop Points */}
          <div className="relative z-10 flex justify-between items-center overflow-x-auto no-scrollbar py-2">
            {STOPS.map((stop, idx) => {
              const isPassed = idx <= activeIdx;
              const isCurrent = idx === activeIdx;
              return (
                <button
                  key={stop.code}
                  onClick={() => setActiveIdx(idx)}
                  className={`flex flex-col items-center gap-1.5 px-2 group focus:outline-none transition-transform ${
                    isCurrent ? 'scale-110' : 'opacity-70 hover:opacity-100'
                  }`}
                >
                  <div
                    className={`w-4 h-4 rounded-none border transition-colors flex items-center justify-center ${
                      isCurrent
                        ? 'bg-[#FFB224] border-[#FFB224]'
                        : isPassed
                        ? 'bg-[#FFB224]/30 border-[#FFB224]'
                        : 'bg-[#15171A] border-[#26282C]'
                    }`}
                  >
                    {isCurrent && <div className="w-1.5 h-1.5 bg-[#0E0F11]" />}
                  </div>
                  <span
                    className={`font-mono text-[10px] tracking-wider uppercase ${
                      isCurrent ? 'text-[#FFB224] font-bold' : 'text-[#9A9DA3]'
                    }`}
                  >
                    {stop.code}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Active Stop Card (Desktop / Tablet view) */}
        <div className="bg-[#15171A] border border-[#26282C] p-6 sm:p-8 rounded-none">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            {/* Left: Group Info & Modules list */}
            <div className="lg:col-span-7 space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 bg-[#1B1D21] border border-[#26282C] flex items-center justify-center text-[#FFB224]">
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <span className="font-mono text-[11px] text-[#FFB224] uppercase tracking-wider">
                    {currentStop.groupName}
                  </span>
                  <h3 className="text-xl font-semibold text-[#E8E8E6]">{currentStop.headline}</h3>
                </div>
              </div>

              <div className="pt-2 border-t border-[#26282C]">
                <div className="text-xs font-mono uppercase text-[#9A9DA3] mb-2 tracking-wider">
                  Included Sub-Modules:
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {currentStop.modules.map(mod => (
                    <div
                      key={mod}
                      className="flex items-center gap-2 text-xs font-mono text-[#E8E8E6] bg-[#0E0F11] border border-[#26282C] px-3 py-2"
                    >
                      <span className="w-1.5 h-1.5 bg-[#FFB224]" />
                      {mod}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right: Live Preview Box */}
            <div className="lg:col-span-5 bg-[#0E0F11] border border-[#26282C] p-5 font-mono text-xs">
              <div className="flex items-center justify-between border-b border-[#26282C] pb-2 mb-3">
                <span className="text-[10px] uppercase text-[#9A9DA3] tracking-wider">
                  {currentStop.previewData.title}
                </span>
                <span className="w-2 h-2 rounded-none bg-[#3ECF8E]" />
              </div>

              <div className="space-y-2 py-2">
                {Object.entries(currentStop.previewData)
                  .filter(([k]) => k !== 'title')
                  .map(([k, v]) => (
                    <div key={k} className="flex items-start justify-between gap-4">
                      <span className="text-[#9A9DA3] uppercase text-[11px]">{k}:</span>
                      <span className="text-[#E8E8E6] font-semibold text-right">{v}</span>
                    </div>
                  ))}
              </div>

              <div className="mt-4 pt-3 border-t border-[#26282C] flex items-center justify-between text-[10px] text-[#9A9DA3]">
                <span>Corridor Node: {currentStop.station}</span>
                <span className="text-[#FFB224]">LIVE STREAM</span>
              </div>
            </div>
          </div>

          {/* Navigation Controls */}
          <div className="mt-8 pt-4 border-t border-[#26282C] flex items-center justify-between">
            <button
              onClick={() => setActiveIdx(prev => (prev > 0 ? prev - 1 : STOPS.length - 1))}
              className="flex items-center gap-2 px-3 py-1.5 bg-[#1B1D21] border border-[#26282C] text-xs font-mono text-[#E8E8E6] hover:border-[#FFB224] transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Previous Stop</span>
            </button>

            <div className="font-mono text-xs text-[#9A9DA3]">
              {activeIdx + 1} / {STOPS.length}
            </div>

            <button
              onClick={() => setActiveIdx(prev => (prev < STOPS.length - 1 ? prev + 1 : 0))}
              className="flex items-center gap-2 px-3 py-1.5 bg-[#1B1D21] border border-[#26282C] text-xs font-mono text-[#FFB224] hover:bg-[#FFB224] hover:text-[#0E0F11] transition-colors"
            >
              <span>Next Stop</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
