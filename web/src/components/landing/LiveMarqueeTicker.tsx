import React, { useEffect, useState } from 'react';
import { mockStore } from '@/mock/store';

export function LiveMarqueeTicker() {
  const [trains, setTrains] = useState(() => mockStore.getTrains().slice(0, 12));

  useEffect(() => {
    const unsub = mockStore.subscribe(() => {
      setTrains(mockStore.getTrains().slice(0, 12));
    });
    return unsub;
  }, []);

  return (
    <div className="w-full bg-[#0E0F11] border-y border-[#26282C] overflow-hidden py-2 select-none">
      <div className="flex items-center gap-2 whitespace-nowrap animate-marquee">
        <span className="bg-[#FFB224] text-[#0E0F11] font-mono text-[10px] font-bold px-2 py-0.5 uppercase tracking-wider mx-2">
          LIVE FEED
        </span>
        {trains.concat(trains).map((train, idx) => {
          const isDelayed = train.delayMinutes > 0;
          return (
            <div
              key={`${train.number}-${idx}`}
              className="inline-flex items-center gap-2 font-mono text-xs text-[#9A9DA3] px-3 border-r border-[#26282C]"
            >
              <span className="text-[#E8E8E6] font-semibold">{train.number}</span>
              <span className="uppercase text-[11px]">{train.name}</span>
              <span className="text-[#9A9DA3]">PF {train.platform}</span>
              <span className="text-[#9A9DA3]">ETA {train.predictedArrival}</span>
              <span
                className={`font-semibold ${
                  isDelayed ? 'text-[#FFB224]' : 'text-[#3ECF8E]'
                }`}
              >
                {isDelayed ? `+${train.delayMinutes}M` : 'ON TIME'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
