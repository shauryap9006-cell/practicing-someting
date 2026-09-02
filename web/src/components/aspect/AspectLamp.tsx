import React from 'react';

export type AspectType = 'clear' | 'caution' | 'restrict' | 'signal';

interface AspectLampProps {
  aspect: AspectType;
  label?: string;
  sublabel?: string;
  pulse?: boolean;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

const ASPECT_COLORS: Record<AspectType, { dot: string; glow: string; text: string; bg: string; border: string }> = {
  clear: {
    dot: 'bg-[#3DDC97]',
    glow: 'shadow-[0_0_8px_rgba(61,220,151,0.6)]',
    text: 'text-[#3DDC97]',
    bg: 'bg-[rgba(61,220,151,0.13)]',
    border: 'border-[#3DDC97]',
  },
  caution: {
    dot: 'bg-[#F5A524]',
    glow: 'shadow-[0_0_8px_rgba(245,165,36,0.6)]',
    text: 'text-[#F5A524]',
    bg: 'bg-[rgba(245,165,36,0.13)]',
    border: 'border-[#F5A524]',
  },
  restrict: {
    dot: 'bg-[#F4506A]',
    glow: 'shadow-[0_0_8px_rgba(244,80,106,0.7)]',
    text: 'text-[#F4506A]',
    bg: 'bg-[rgba(244,80,106,0.13)]',
    border: 'border-[#F4506A]',
  },
  signal: {
    dot: 'bg-[#6C9FFF]',
    glow: 'shadow-[0_0_8px_rgba(108,159,255,0.6)]',
    text: 'text-[#6C9FFF]',
    bg: 'bg-[rgba(108,159,255,0.13)]',
    border: 'border-[#6C9FFF]',
  },
};

const DOT_SIZES = {
  xs: 'w-1.5 h-1.5',
  sm: 'w-2 h-2',
  md: 'w-2.5 h-2.5',
  lg: 'w-3 h-3',
};

const TEXT_SIZES = {
  xs: 'text-[10px]',
  sm: 'text-[11px]',
  md: 'text-xs',
  lg: 'text-sm',
};

export const AspectLamp: React.FC<AspectLampProps> = ({
  aspect,
  label,
  sublabel,
  pulse = false,
  size = 'sm',
  showLabel = true,
  className = '',
}) => {
  const config = ASPECT_COLORS[aspect] || ASPECT_COLORS.caution;
  const dotSizeClass = DOT_SIZES[size];
  const textSizeClass = TEXT_SIZES[size];

  const defaultLabels: Record<AspectType, string> = {
    clear: 'CLEAR',
    caution: 'CAUTION',
    restrict: 'RESTRICT',
    signal: 'SIGNAL',
  };

  const displayLabel = label ?? defaultLabels[aspect];

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono uppercase tracking-wider tabular-nums font-semibold select-none ${className}`}
      aria-label={`Signal Aspect: ${displayLabel}`}
    >
      <span className="relative flex items-center justify-center">
        {pulse && (
          <span
            className={`absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping ${config.dot}`}
          />
        )}
        <span
          className={`relative inline-block rounded-full ${dotSizeClass} ${config.dot} ${config.glow}`}
        />
      </span>
      {showLabel && (
        <span className={`${config.text} ${textSizeClass}`}>
          {displayLabel}
          {sublabel && <span className="ml-1 text-[10px] text-text-3 font-normal">({sublabel})</span>}
        </span>
      )}
    </span>
  );
};
