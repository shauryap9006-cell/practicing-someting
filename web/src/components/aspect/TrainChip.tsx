import React from 'react';
import { AspectLamp, AspectType } from './AspectLamp';

export interface TrainChipData {
  id?: string;
  trainNo: string;
  trainName?: string;
  delayMin: number;
  aspect?: AspectType;
  platform?: number | string;
  km?: number;
  direction?: 'UP' | 'DN';
}

interface TrainChipProps {
  train: TrainChipData;
  onClick?: (train: TrainChipData) => void;
  selected?: boolean;
  density?: 'compact' | 'regular' | 'large';
  showName?: boolean;
  showPlatform?: boolean;
  className?: string;
}

export const TrainChip: React.FC<TrainChipProps> = ({
  train,
  onClick,
  selected = false,
  density = 'regular',
  showName = true,
  showPlatform = false,
  className = '',
}) => {
  const getAspect = (): AspectType => {
    if (train.aspect) return train.aspect;
    if (train.delayMin <= 5) return 'clear';
    if (train.delayMin <= 25) return 'caution';
    return 'restrict';
  };

  const aspect = getAspect();
  const isClear = aspect === 'clear';
  const delayStr = isClear ? 'ON TIME' : `+${train.delayMin}M`;

  return (
    <button
      type="button"
      onClick={() => onClick?.(train)}
      className={`group relative inline-flex items-center gap-2 border font-mono transition-all duration-120 select-none ${
        density === 'compact'
          ? 'px-2 py-1 text-xs rounded-sm'
          : density === 'large'
          ? 'px-3.5 py-2 text-sm rounded-md'
          : 'px-2.5 py-1.5 text-xs rounded-sm'
      } ${
        selected
          ? 'bg-[#15181D] border-[#F5A524] shadow-[0_0_0_1px_#F5A524]'
          : 'bg-[#101216] border-[#23272F] hover:border-[#2E333D] hover:bg-[#15181D]'
      } ${className}`}
    >
      <span className="font-bold text-[#E9EBEE] tracking-tight">{train.trainNo}</span>

      {showName && train.trainName && (
        <span className="text-[#A3ABB6] font-sans text-xs truncate max-w-[120px] sm:max-w-[160px]">
          {train.trainName}
        </span>
      )}

      {showPlatform && train.platform && (
        <span className="px-1 py-0.5 text-[10px] bg-[#1B1F26] border border-[#23272F] text-[#6B7480]">
          PF-{train.platform}
        </span>
      )}

      <AspectLamp
        aspect={aspect}
        label={delayStr}
        size={density === 'compact' ? 'xs' : 'sm'}
      />
    </button>
  );
};
