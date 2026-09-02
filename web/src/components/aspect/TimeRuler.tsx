import React, { useState } from 'react';
import { AspectLamp, AspectType } from './AspectLamp';

export interface TimeSlot {
  id: string;
  trainNo: string;
  trainName?: string;
  platform: number;
  scheduledArrival: string; // "18:20"
  scheduledDeparture: string; // "18:35"
  estimatedArrival?: string;
  estimatedDeparture?: string;
  delayMin: number;
  isConflict?: boolean;
  conflictWith?: string;
  aspect?: AspectType;
  swappedPlatform?: number;
}

interface TimeRulerProps {
  slots: TimeSlot[];
  platformsCount?: number;
  startHour?: number; // e.g. 17 (17:00)
  hoursSpan?: number; // e.g. 4 hours
  onSelectSlot?: (slot: TimeSlot) => void;
  selectedSlotId?: string;
  isOptimizing?: boolean;
  className?: string;
}

export const TimeRuler: React.FC<TimeRulerProps> = ({
  slots,
  platformsCount = 6,
  startHour = 17,
  hoursSpan = 4,
  onSelectSlot,
  selectedSlotId,
  isOptimizing = false,
  className = '',
}) => {
  const [hoveredSlot, setHoveredSlot] = useState<TimeSlot | null>(null);

  // Convert time string "HH:MM" to minute offset from startHour:00
  const timeToMinutes = (timeStr: string): number => {
    if (!timeStr) return 0;
    const parts = timeStr.split(':');
    const h = parseInt(parts[0], 10);
    const m = parseInt(parts[1] || '0', 10);
    return (h - startHour) * 60 + m;
  };

  const totalMinutes = hoursSpan * 60;

  const getSlotPercentage = (timeStr: string) => {
    const mins = timeToMinutes(timeStr);
    const clamped = Math.max(0, Math.min(totalMinutes, mins));
    return (clamped / totalMinutes) * 100;
  };

  const getAspect = (slot: TimeSlot): AspectType => {
    if (slot.isConflict) return 'restrict';
    if (slot.aspect) return slot.aspect;
    if (slot.delayMin <= 5) return 'clear';
    if (slot.delayMin <= 25) return 'caution';
    return 'restrict';
  };

  // Generate hour markers
  const hourTicks = Array.from({ length: hoursSpan + 1 }, (_, i) => {
    const h = (startHour + i) % 24;
    return `${h.toString().padStart(2, '0')}:00`;
  });

  return (
    <div className={`bg-[#101216] border border-[#23272F] rounded-lg p-5 font-mono select-none ${className}`}>
      {/* Time Axis Header */}
      <div className="relative w-full h-8 border-b border-[#23272F] mb-3">
        <div className="absolute inset-0 flex justify-between items-center text-xs text-[#6B7480] px-12">
          {hourTicks.map((tick, i) => (
            <div key={tick} className="flex flex-col items-center">
              <span className="font-bold text-[#A3ABB6]">{tick}</span>
              <div className="w-[1px] h-2 bg-[#2E333D] mt-1" />
            </div>
          ))}
        </div>
      </div>

      {/* Platform Rows / Lanes */}
      <div className="space-y-2">
        {Array.from({ length: platformsCount }, (_, pIdx) => {
          const platformNum = pIdx + 1;
          const platformSlots = slots.filter(s => s.platform === platformNum);

          return (
            <div
              key={platformNum}
              className="relative flex items-center h-12 bg-[#0A0B0D] border border-[#23272F] rounded-sm group hover:border-[#2E333D] transition-colors"
            >
              {/* Platform Label Tag */}
              <div className="w-12 h-full flex items-center justify-center bg-[#15181D] border-r border-[#23272F] text-xs font-bold text-[#E9EBEE] shrink-0">
                PF-{platformNum}
              </div>

              {/* Lane Timeline Track */}
              <div className="relative flex-1 h-full overflow-hidden">
                {/* 15-minute subtle grid guides */}
                <div className="absolute inset-0 flex justify-between pointer-events-none opacity-10">
                  {Array.from({ length: hoursSpan * 4 }, (_, gIdx) => (
                    <div key={gIdx} className="w-[1px] h-full bg-[#E9EBEE]" />
                  ))}
                </div>

                {/* Train Blocks on Lane */}
                {platformSlots.map(slot => {
                  const arrPct = getSlotPercentage(slot.estimatedArrival || slot.scheduledArrival);
                  const depPct = getSlotPercentage(slot.estimatedDeparture || slot.scheduledDeparture);
                  const widthPct = Math.max(8, depPct - arrPct);
                  const aspect = getAspect(slot);
                  const isSelected = selectedSlotId === slot.id;

                  return (
                    <button
                      key={slot.id}
                      type="button"
                      onClick={() => onSelectSlot?.(slot)}
                      onMouseEnter={() => setHoveredSlot(slot)}
                      onMouseLeave={() => setHoveredSlot(null)}
                      className={`absolute top-1.5 bottom-1.5 rounded-sm border px-2 flex items-center justify-between text-left transition-all duration-300 track-slide ${
                        aspect === 'clear'
                          ? 'bg-[rgba(61,220,151,0.18)] border-[#3DDC97] text-[#E9EBEE]'
                          : aspect === 'restrict'
                          ? 'bg-[rgba(244,80,106,0.22)] border-[#F4506A] text-[#E9EBEE] aspect-pulse-restrict'
                          : 'bg-[rgba(245,165,36,0.18)] border-[#F5A524] text-[#E9EBEE]'
                      } ${
                        isSelected
                          ? 'ring-2 ring-[#E9EBEE] z-20 shadow-lg'
                          : 'hover:brightness-125 z-10'
                      }`}
                      style={{
                        left: `${arrPct}%`,
                        width: `${widthPct}%`,
                      }}
                    >
                      <div className="flex items-center gap-1.5 truncate">
                        <span className="font-bold text-xs">{slot.trainNo}</span>
                        {slot.trainName && (
                          <span className="hidden sm:inline text-[10px] text-[#A3ABB6] truncate font-sans">
                            {slot.trainName}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-1 shrink-0 ml-1">
                        {slot.isConflict && (
                          <span className="px-1 py-0.2 bg-[#F4506A] text-[#0A0B0D] font-bold text-[9px] rounded-xs animate-pulse">
                            CONFLICT
                          </span>
                        )}
                        <AspectLamp aspect={aspect} showLabel={false} size="xs" />
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Hovered Slot Inspection Bar */}
      {hoveredSlot && (
        <div className="mt-4 pt-3 border-t border-[#23272F] flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-3">
            <span className="font-bold text-[#E9EBEE]">{hoveredSlot.trainNo} {hoveredSlot.trainName}</span>
            <span className="text-[#A3ABB6]">
              PF-{hoveredSlot.platform} · Arr: {hoveredSlot.estimatedArrival || hoveredSlot.scheduledArrival} · Dep: {hoveredSlot.estimatedDeparture || hoveredSlot.scheduledDeparture}
            </span>
          </div>
          <div className="flex items-center gap-3">
            {hoveredSlot.isConflict ? (
              <span className="text-[#F4506A] font-bold">
                ● CONFLICT WITH {hoveredSlot.conflictWith || 'CONCURRENT DWELL'}
              </span>
            ) : (
              <AspectLamp
                aspect={getAspect(hoveredSlot)}
                label={hoveredSlot.delayMin <= 0 ? 'ON TIME' : `+${hoveredSlot.delayMin}M DELAY`}
                size="xs"
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
};
