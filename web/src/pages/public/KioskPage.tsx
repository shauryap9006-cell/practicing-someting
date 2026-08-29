import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Train } from '@/mock/types';
import { formatTimeIST } from '@/lib/utils';
import { DataFreshnessBadge } from '@/components/common/DataFreshnessBadge';
import { Maximize2, Minimize2, Radio, Volume2 } from 'lucide-react';
import { SEO } from '@/lib/seo';

export function KioskPage() {
  const { data: rawTrains = [], dataUpdatedAt } = useQuery({
    queryKey: queryKeys.board('CNB'),
    queryFn: () => api.getTrains(),
  });
  const trains = rawTrains.slice(0, 8);
  const [time, setTime] = useState(() => formatTimeIST(new Date()));
  const [station] = useState('KANPUR CENTRAL (CNB)');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [viewMode, setViewMode] = useState<'board' | 'announcement'>('board');

  useEffect(() => {
    // 1-second clock
    const clockTimer = setInterval(() => {
      setTime(formatTimeIST(new Date()));
    }, 1000);

    // 12-second auto-rotate board <-> announcement
    const rotateTimer = setInterval(() => {
      setViewMode(prev => (prev === 'board' ? 'announcement' : 'board'));
    }, 12000);

    return () => {
      clearInterval(clockTimer);
      clearInterval(rotateTimer);
    };
  }, []);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0E0F11] text-[#E8E8E6] flex flex-col justify-between p-6 sm:p-10 select-none overflow-hidden font-sans">
      <SEO title="Station Kiosk PIDS · RailTwin-X" noindex />

      {/* Header: Station Code & Giant Live Clock */}
      <header className="border-b-2 border-[#26282C] pb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-4 h-4 bg-[#FFB224] animate-pulse" />
          <div>
            <span className="font-mono text-sm uppercase tracking-widest text-[#FFB224]">
              INDIAN RAILWAYS · PASSENGER INFORMATION DISPLAY SYSTEM (PIDS)
            </span>
            <h1 className="text-3xl sm:text-5xl font-bold tracking-tight text-[#E8E8E6] mt-1">
              {station}
            </h1>
            <div className="mt-1">
              <DataFreshnessBadge dataUpdatedAt={dataUpdatedAt} />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="text-right">
            <span className="font-mono text-xs uppercase text-[#9A9DA3] tracking-widest block">
              INDIAN STANDARD TIME
            </span>
            <div className="font-mono text-4xl sm:text-6xl font-bold text-[#FFB224] tabular-nums">
              {time}
            </div>
          </div>

          <button
            onClick={toggleFullscreen}
            className="p-3 bg-[#15171A] border border-[#26282C] hover:border-[#FFB224] text-[#9A9DA3] hover:text-[#E8E8E6] transition-colors"
            title="Toggle Fullscreen"
          >
            {isFullscreen ? <Minimize2 className="w-6 h-6" /> : <Maximize2 className="w-6 h-6" />}
          </button>
        </div>
      </header>

      {/* Main Screen: Departures Board OR Multilingual Announcement */}
      <main className="my-auto py-6">
        {viewMode === 'board' ? (
          <div className="border-2 border-[#26282C] bg-[#15171A]">
            {/* Table Header */}
            <div className="grid grid-cols-12 bg-[#1B1D21] border-b-2 border-[#26282C] py-4 px-6 font-mono text-sm sm:text-base font-bold uppercase text-[#9A9DA3] tracking-wider">
              <div className="col-span-2">Train No</div>
              <div className="col-span-4">Train Name / Destination</div>
              <div className="col-span-2 text-center">Platform</div>
              <div className="col-span-2 text-right">Expected</div>
              <div className="col-span-2 text-right">Status</div>
            </div>

            {/* Train Rows (3-meter readable typography) */}
            <div className="divide-y divide-[#26282C]">
              {trains.map((train, idx) => {
                const isDelayed = train.delayMinutes > 0;
                return (
                  <div
                    key={train.number}
                    className={`grid grid-cols-12 py-5 px-6 items-center transition-colors ${
                      idx % 2 === 0 ? 'bg-[#15171A]' : 'bg-[#121316]'
                    }`}
                  >
                    <div className="col-span-2 font-mono text-2xl sm:text-4xl font-bold text-[#E8E8E6]">
                      {train.number}
                    </div>

                    <div className="col-span-4">
                      <div className="text-xl sm:text-2xl font-bold text-[#E8E8E6] truncate">
                        {train.name}
                      </div>
                      <div className="font-mono text-xs sm:text-sm text-[#9A9DA3] uppercase tracking-wider">
                        To {train.destination}
                      </div>
                    </div>

                    <div className="col-span-2 text-center">
                      <span className="font-mono text-3xl sm:text-5xl font-black text-[#FFB224] bg-[#FFB224]/10 px-4 py-1 border border-[#FFB224]">
                        {train.platform}
                      </span>
                    </div>

                    <div className="col-span-2 text-right font-mono text-2xl sm:text-3xl font-bold text-[#E8E8E6] tabular-nums">
                      {train.predictedArrival}
                    </div>

                    <div className="col-span-2 text-right font-mono text-xl sm:text-2xl font-bold">
                      {isDelayed ? (
                        <span className="text-[#FFB224] bg-[#FFB224]/10 px-3 py-1 border border-[#FFB224]">
                          LATE {train.delayMinutes}M
                        </span>
                      ) : (
                        <span className="text-[#3ECF8E] bg-[#3ECF8E]/10 px-3 py-1 border border-[#3ECF8E]">
                          ON TIME
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          /* Multilingual Announcement Banner View */
          <div className="border-2 border-[#FFB224] bg-[#15171A] p-10 sm:p-16 flex flex-col justify-center items-center text-center space-y-8 animate-fadeIn">
            <div className="flex items-center gap-3 text-[#FFB224]">
              <Volume2 className="w-10 h-10 animate-bounce" />
              <span className="font-mono text-lg uppercase tracking-widest font-bold">
                STATION PUBLIC ADDRESS SYSTEM · उद्घोषणा
              </span>
            </div>

            {/* Hindi Script */}
            <div className="text-2xl sm:text-4xl font-bold text-[#E8E8E6] leading-relaxed max-w-5xl">
              कृपया ध्यान दीजिए! गाड़ी संख्या <span className="text-[#FFB224]">12034 नई दिल्ली - कानपुर शताब्दी</span>, 
              कुछ ही समय में प्लेटफार्म संख्या <span className="text-[#FFB224] text-5xl">3</span> पर आ रही है।
            </div>

            {/* English Script */}
            <div className="text-xl sm:text-3xl font-semibold text-[#9A9DA3] leading-relaxed max-w-5xl">
              Your kind attention please! Train number <span className="text-[#FFB224]">12034 New Delhi - Kanpur Shatabdi</span> is arriving shortly on Platform Number <span className="text-[#FFB224] text-4xl">3</span>.
            </div>
          </div>
        )}
      </main>

      {/* Kiosk Footer */}
      <footer className="border-t-2 border-[#26282C] pt-4 flex flex-col sm:flex-row items-center justify-between font-mono text-xs sm:text-sm text-[#9A9DA3]">
        <div className="flex items-center gap-3">
          <Radio className="w-4 h-4 text-[#3ECF8E] animate-pulse" />
          <span>LIVE TELEMETRY STREAM · REFRESH 5S · HIGH-CONTRAST MODE</span>
        </div>
        <div className="mt-2 sm:mt-0 text-[#E8E8E6]">
          ADVISORY ONLY · Powered by <span className="text-[#FFB224] font-bold">RailTwin-X</span>
        </div>
      </footer>
    </div>
  );
}
