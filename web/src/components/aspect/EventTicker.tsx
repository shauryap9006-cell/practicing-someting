import React from 'react';

export interface TickerEvent {
  id: string;
  time: string;
  message: string;
  tag?: string;
  type?: 'clear' | 'caution' | 'restrict' | 'signal';
}

const DEFAULT_EVENTS: TickerEvent[] = [
  {
    id: '1',
    time: '17:50:12',
    message: 'TSR lifted ETW–TDL km 296 → 6 active trains recovered 4m average runtime',
    tag: 'TSR RECOVERY',
    type: 'clear',
  },
  {
    id: '2',
    time: '17:48:30',
    message: 'Platform 3 CNB allocated to 12034 Shatabdi Express · Inbound from ALJN',
    tag: 'PLATFORM ALLOC',
    type: 'signal',
  },
  {
    id: '3',
    time: '17:45:19',
    message: 'Freight Precedence hold cleared at Tundla Junction for 22436 Vande Bharat',
    tag: 'DISPATCH',
    type: 'clear',
  },
  {
    id: '4',
    time: '17:42:01',
    message: 'Crew relief alert: LP Sharma 12301 assigned relief crew at Kanpur Central',
    tag: 'CREW RELIEF',
    type: 'caution',
  },
  {
    id: '5',
    time: '17:39:55',
    message: 'Fog density index updated: Visibility >1200m along GZB–ALJN section',
    tag: 'WEATHER',
    type: 'signal',
  },
];

interface EventTickerProps {
  events?: TickerEvent[];
  className?: string;
}

export const EventTicker: React.FC<EventTickerProps> = ({
  events = DEFAULT_EVENTS,
  className = '',
}) => {
  return (
    <div
      className={`w-full bg-[#0A0B0D] border-y border-[#23272F] py-2 px-4 flex items-center overflow-hidden font-mono text-xs select-none ${className}`}
    >
      {/* Live Badge */}
      <div className="flex items-center gap-2 pr-4 border-r border-[#23272F] shrink-0">
        <span className="w-2 h-2 rounded-full bg-[#F5A524] shadow-[0_0_8px_rgba(245,165,36,0.6)] animate-pulse" />
        <span className="font-bold text-[#E9EBEE] uppercase tracking-wider text-[10px]">
          LIVE TELEMETRY FEED
        </span>
      </div>

      {/* Marquee Content */}
      <div className="relative flex-1 overflow-hidden whitespace-nowrap pl-4">
        <div className="inline-flex gap-8 animate-marquee">
          {events.concat(events).map((ev, idx) => (
            <div key={`${ev.id}-${idx}`} className="inline-flex items-center gap-2 text-xs">
              <span className="text-[#6B7480]">{ev.time}</span>
              {ev.tag && (
                <span
                  className={`px-1.5 py-0.2 rounded-xs text-[10px] font-bold ${
                    ev.type === 'clear'
                      ? 'bg-[#3DDC97]/15 text-[#3DDC97] border border-[#3DDC97]/30'
                      : ev.type === 'restrict'
                      ? 'bg-[#F4506A]/15 text-[#F4506A] border border-[#F4506A]/30'
                      : ev.type === 'caution'
                      ? 'bg-[#F5A524]/15 text-[#F5A524] border border-[#F5A524]/30'
                      : 'bg-[#6C9FFF]/15 text-[#6C9FFF] border border-[#6C9FFF]/30'
                  }`}
                >
                  {ev.tag}
                </span>
              )}
              <span className="text-[#E9EBEE] font-sans text-xs">{ev.message}</span>
              <span className="text-[#2E333D] font-mono">/</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
