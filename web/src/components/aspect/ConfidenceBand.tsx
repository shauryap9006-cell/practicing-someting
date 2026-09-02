import React from 'react';

interface ConfidenceBandProps {
  expectedTime: string; // e.g. "18:22"
  rangeStart: string; // e.g. "18:15"
  rangeEnd: string; // e.g. "19:05"
  size?: 'inline' | 'card' | 'giant';
  showLabel?: boolean;
  className?: string;
}

export const ConfidenceBand: React.FC<ConfidenceBandProps> = ({
  expectedTime,
  rangeStart,
  rangeEnd,
  size = 'card',
  showLabel = true,
  className = '',
}) => {
  return (
    <div className={`font-mono select-none ${className}`}>
      {showLabel && (
        <span className="block text-[10px] uppercase tracking-widest text-[#6B7480] mb-0.5">
          Expected Arrival
        </span>
      )}

      {/* Main ETA Value */}
      <div
        className={`font-bold tabular-nums text-[#E9EBEE] tracking-tight ${
          size === 'giant'
            ? 'text-5xl sm:text-7xl lg:text-8xl text-[#F5A524]'
            : size === 'inline'
            ? 'text-base sm:text-lg'
            : 'text-2xl sm:text-3xl'
        }`}
      >
        {expectedTime}
      </div>

      {/* Confidence Window Band (Signal Blue Tint) */}
      <div
        className={`inline-flex items-center gap-1.5 px-2 py-0.5 mt-1 rounded-sm bg-[rgba(108,159,255,0.13)] border border-[#6C9FFF]/40 text-[#6C9FFF] ${
          size === 'giant' ? 'text-sm sm:text-base px-3 py-1 font-semibold' : 'text-xs'
        }`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-[#6C9FFF]" />
        <span>
          between <span className="font-bold">{rangeStart}</span> – <span className="font-bold">{rangeEnd}</span>
        </span>
      </div>
    </div>
  );
};
