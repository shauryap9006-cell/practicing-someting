import React, { useEffect, useState } from 'react';

const BOOT_KEY = 'rtx_boot_preloaded_session';

export function BootPreloader({ onComplete }: { onComplete: () => void }) {
  const [lines, setLines] = useState<string[]>([]);
  const [isWiping, setIsWiping] = useState(false);

  useEffect(() => {
    // Check if already seen in this session or reduced motion
    const seen = sessionStorage.getItem(BOOT_KEY);
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (seen || prefersReduced) {
      onComplete();
      return;
    }

    const script = [
      'INITIALIZING CORRIDOR TELEMETRY …',
      'TRACK ALIGNMENT: NDLS — GZB — ALJN — TDL — ETW — CNB — PRYJ — DDU',
      'INTERLOCKING STATUS: SIGNALS ONLINE · 10 PLATFORMS LINKED',
      'TRAIN TRACKING ENGINE: 55+ PASSENGER & DFC FREIGHT RAKES ACTIVE',
      'SYSTEM READY · ALLOCATING ADVISORY CO-PROCESSOR',
    ];

    let current = 0;
    const interval = setInterval(() => {
      if (current < script.length) {
        setLines(prev => [...prev, script[current]]);
        current++;
      } else {
        clearInterval(interval);
        setTimeout(() => {
          setIsWiping(true);
          sessionStorage.setItem(BOOT_KEY, '1');
          setTimeout(onComplete, 400);
        }, 300);
      }
    }, 140);

    return () => clearInterval(interval);
  }, [onComplete]);

  return (
    <div
      className={`fixed inset-0 z-50 bg-[#0E0F11] flex flex-col justify-end p-8 font-mono text-xs transition-transform duration-500 ease-in-out ${
        isWiping ? '-translate-y-full opacity-0' : 'translate-y-0 opacity-100'
      }`}
    >
      <div className="max-w-2xl w-full mx-auto space-y-2 mb-8">
        <div className="flex items-center justify-between border-b border-[#26282C] pb-2 mb-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-none bg-[#FFB224] animate-pulse" />
            <span className="font-semibold text-[#E8E8E6] tracking-wider uppercase">RailTwin-X Control OS Boot</span>
          </div>
          <button
            onClick={() => {
              sessionStorage.setItem(BOOT_KEY, '1');
              onComplete();
            }}
            className="text-[11px] text-[#9A9DA3] hover:text-[#FFB224] transition-colors"
          >
            [Skip Esc]
          </button>
        </div>

        {lines.map((l, idx) => (
          <div key={idx} className="flex items-start gap-2 text-[#9A9DA3]">
            <span className="text-[#FFB224] select-none">&gt;</span>
            <span className={idx === lines.length - 1 ? 'text-[#E8E8E6]' : ''}>{l}</span>
          </div>
        ))}

        <div className="flex items-center gap-1 text-[#FFB224] mt-2">
          <span>&gt;</span>
          <span className="w-2 h-3.5 bg-[#FFB224] animate-pulse" />
        </div>
      </div>
    </div>
  );
}
