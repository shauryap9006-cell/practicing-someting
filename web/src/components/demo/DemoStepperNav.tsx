import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Zap,
  GitFork,
  Layers,
  History,
  ShieldCheck,
  ChevronRight,
  Home,
} from 'lucide-react';

export interface DemoStep {
  id: string;
  stepNumber: number;
  label: string;
  tagline: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  accentColor: string;
}

export const DEMO_STEPS: DemoStep[] = [
  {
    id: 'foresight',
    stepNumber: 1,
    label: 'Foresight Console',
    tagline: 'Cones, Shocks & Radar',
    path: '/foresight',
    icon: Zap,
    accentColor: '#FFB224',
  },
  {
    id: 'compare',
    stepNumber: 2,
    label: 'Live Comparator',
    tagline: 'RailTwin-X vs NTES',
    path: '/compare',
    icon: GitFork,
    accentColor: '#60A5FA',
  },
  {
    id: 'cascade',
    stepNumber: 3,
    label: 'Ripple & Custody',
    tagline: 'Rake Deficits & DSS',
    path: '/cascade',
    icon: Layers,
    accentColor: '#A78BFA',
  },
  {
    id: 'time-machine',
    stepNumber: 4,
    label: 'Time Machine',
    tagline: 'Ledger Checkpoint Replay',
    path: '/time-machine',
    icon: History,
    accentColor: '#F472B6',
  },
  {
    id: 'model-card',
    stepNumber: 5,
    label: 'Honest Model Card',
    tagline: 'Crypto Proofs & Integrity',
    path: '/model-card',
    icon: ShieldCheck,
    accentColor: '#34D399',
  },
];

interface DemoStepperNavProps {
  className?: string;
  compact?: boolean;
}

export const DemoStepperNav: React.FC<DemoStepperNavProps> = ({ className = '', compact = false }) => {
  const location = useLocation();

  const currentStepIndex = DEMO_STEPS.findIndex(
    (step) => step.path === location.pathname
  );

  return (
    <nav
      aria-label="SIH Jury 5-Beat Demo Stepper"
      className={`bg-[#0C0F17]/95 border-b border-white/10 backdrop-blur-md px-3 sm:px-4 py-2 font-mono text-xs ${className}`}
    >
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-2.5">
        {/* Banner Label & Home Return */}
        <div className="flex items-center gap-2.5 shrink-0">
          <Link
            to="/"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white border border-white/10 transition-colors text-[11px] font-bold"
            title="Return to Main Landing Page"
          >
            <Home className="w-3.5 h-3.5 text-[#FFB224]" />
            <span>Landing</span>
          </Link>
          <span className="text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 rounded bg-[#FFB224]/10 text-[#FFB224] border border-[#FFB224]/30">
            Jury Demo Sequence
          </span>
          <span className="text-gray-400 text-[11px] hidden sm:inline">
            5-Beat Evaluation Flow
          </span>
        </div>

        {/* The 5 Steps */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-none">
          {DEMO_STEPS.map((step, idx) => {
            const isActive = idx === currentStepIndex;
            const isCompleted = currentStepIndex !== -1 && idx < currentStepIndex;

            return (
              <React.Fragment key={step.id}>
                <Link
                  to={step.path}
                  className={`flex items-center gap-2 px-2.5 py-1.5 rounded-md transition-all whitespace-nowrap group ${
                    isActive
                      ? 'bg-white/10 border border-white/20 text-white shadow-lg ring-1 ring-white/10'
                      : 'bg-[#12151E] hover:bg-[#181D29] text-gray-400 hover:text-gray-200 border border-white/5'
                  }`}
                  style={{
                    borderLeftColor: isActive ? step.accentColor : undefined,
                    borderLeftWidth: isActive ? '3px' : undefined,
                  }}
                >
                  <div
                    className="w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold"
                    style={{
                      backgroundColor: isActive ? `${step.accentColor}25` : '#1A1E29',
                      color: isActive ? step.accentColor : '#9CA3AF',
                    }}
                  >
                    {isCompleted ? '✓' : step.stepNumber}
                  </div>
                  <div>
                    <div className="flex items-center gap-1">
                      <span className="font-bold text-[11px]">{step.label}</span>
                      {isActive && (
                        <span
                          className="w-1.5 h-1.5 rounded-full animate-ping"
                          style={{ backgroundColor: step.accentColor }}
                        />
                      )}
                    </div>
                    {!compact && (
                      <div className="text-[9px] text-gray-400 leading-none">
                        {step.tagline}
                      </div>
                    )}
                  </div>
                </Link>

                {idx < DEMO_STEPS.length - 1 && (
                  <ChevronRight className="w-3 h-3 text-gray-600 shrink-0 hidden sm:block" />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </nav>
  );
};
