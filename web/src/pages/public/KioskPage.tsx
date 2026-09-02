import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Train } from '@/mock/types';
import { formatTimeIST } from '@/lib/utils';
import {
  AspectLamp,
  AspectType,
  ConfidenceBand,
  Provenance,
} from '@/components/aspect';
import { Maximize2, Minimize2, Radio, Volume2, Languages } from 'lucide-react';
import { SEO } from '@/lib/seo';

const KIOSK_TRAINS_SAMPLE = [
  {
    trainNo: '12034',
    trainName: 'Kanpur Shatabdi Express',
    trainNameHi: 'कानपुर शताब्दी एक्सप्रेस',
    dest: 'Kanpur Central',
    destHi: 'कानपुर सेंट्रल',
    expected: '18:22',
    rangeStart: '18:15',
    rangeEnd: '19:05',
    delayMin: 18,
    platform: 3,
    minAway: 12,
    reason: 'Speed restriction near Etawah',
    reasonHi: 'इटावा के पास गति प्रतिबंध',
  },
  {
    trainNo: '22436',
    trainName: 'Vande Bharat Express',
    trainNameHi: 'वंदे भारत एक्सप्रेस',
    dest: 'Varanasi Junction',
    destHi: 'वाराणसी जंक्शन',
    expected: '18:40',
    rangeStart: '18:38',
    rangeEnd: '18:43',
    delayMin: 0,
    platform: 1,
    minAway: 30,
    reason: 'On-time section running',
    reasonHi: 'समय पर परिचालन',
  },
  {
    trainNo: '12301',
    trainName: 'Howrah Rajdhani Express',
    trainNameHi: 'हावड़ा राजधानी एक्सप्रेस',
    dest: 'Howrah Junction',
    destHi: 'हावड़ा जंक्शन',
    expected: '19:42',
    rangeStart: '19:20',
    rangeEnd: '20:05',
    delayMin: 27,
    platform: 2,
    minAway: 92,
    reason: 'Congestion after Kanpur yard',
    reasonHi: 'कानपुर यार्ड के पास भीड़भाड़',
  },
];

export function KioskPage() {
  const { data: rawTrains = [], dataUpdatedAt } = useQuery({
    queryKey: queryKeys.board('CNB'),
    queryFn: () => api.getTrains(),
    refetchInterval: 5000,
  });

  const [time, setTime] = useState(() => formatTimeIST(new Date()));
  const [station] = useState('KANPUR CENTRAL (CNB)');
  const [stationHi] = useState('कानपुर सेंट्रल (CNB)');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [lang, setLang] = useState<'EN' | 'HI'>('EN');
  const [activeTrainIndex, setActiveTrainIndex] = useState(0);

  useEffect(() => {
    // 1-second clock
    const clockTimer = setInterval(() => {
      setTime(formatTimeIST(new Date()));
    }, 1000);

    // 8-second auto-cycle highlighted train
    const trainTimer = setInterval(() => {
      setActiveTrainIndex(prev => (prev + 1) % KIOSK_TRAINS_SAMPLE.length);
    }, 8000);

    return () => {
      clearInterval(clockTimer);
      clearInterval(trainTimer);
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

  const activeTrain = KIOSK_TRAINS_SAMPLE[activeTrainIndex];
  const aspect: AspectType = activeTrain.delayMin <= 5 ? 'clear' : activeTrain.delayMin <= 25 ? 'caution' : 'restrict';

  return (
    <div className="min-h-screen bg-[#0A0B0D] text-[#E9EBEE] flex flex-col justify-between p-4 sm:p-8 select-none font-mono">
      <SEO title="Passenger PIDS Display · RailTwin-X" noindex />

      {/* Top Station Header & Giant Clock */}
      <header className="border-b border-[#23272F] pb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="w-3 h-3 rounded-full bg-[#F5A524] shadow-[0_0_8px_rgba(245,165,36,0.6)] animate-pulse" />
          <div>
            <span className="text-[10px] sm:text-xs uppercase tracking-widest text-[#F5A524] font-bold block">
              {lang === 'EN'
                ? 'INDIAN RAILWAYS · PASSENGER INFORMATION DISPLAY SYSTEM'
                : 'भारतीय रेल · यात्री सूचना प्रणाली'}
            </span>
            <h1 className="text-xl sm:text-3xl font-bold tracking-tight text-[#E9EBEE] font-display mt-0.5">
              {lang === 'EN' ? station : stationHi}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Language Toggle Button */}
          <button
            type="button"
            onClick={() => setLang(l => (l === 'EN' ? 'HI' : 'EN'))}
            className="px-2.5 py-1 bg-[#101216] border border-[#23272F] hover:border-[#F5A524] text-xs font-bold text-[#E9EBEE] rounded-sm transition-colors flex items-center gap-1.5"
          >
            <Languages className="w-3.5 h-3.5 text-[#F5A524]" />
            <span>{lang === 'EN' ? 'हिंदी' : 'ENGLISH'}</span>
          </button>

          {/* Clock */}
          <div className="text-right">
            <div className="text-2xl sm:text-4xl font-bold text-[#F5A524] tabular-nums">
              {time}
            </div>
            <span className="text-[9px] text-[#6B7480] uppercase tracking-wider block">
              IST · INDIAN STANDARD TIME
            </span>
          </div>

          <button
            type="button"
            onClick={toggleFullscreen}
            className="p-2 bg-[#101216] border border-[#23272F] hover:border-[#F5A524] text-[#A3ABB6] hover:text-[#E9EBEE] rounded-sm transition-colors"
            title="Toggle Fullscreen"
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </header>

      {/* Main Center Instrument: Giant Mode Focus Train */}
      <main className="my-auto py-8">
        <div className="max-w-4xl mx-auto bg-[#101216] border border-[#23272F] rounded-lg p-6 sm:p-10 space-y-6 shadow-2xl">
          {/* Train Identity Banner */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[#23272F]">
            <div>
              <div className="flex items-center gap-3">
                <span className="text-2xl sm:text-4xl font-bold text-[#E9EBEE] tracking-tight">
                  🚆 {activeTrain.trainNo}
                </span>
                <span className="text-lg sm:text-2xl font-sans text-[#A3ABB6]">
                  {lang === 'EN' ? activeTrain.trainName : activeTrain.trainNameHi}
                </span>
              </div>
              <span className="text-xs sm:text-sm text-[#F5A524] mt-1 block">
                → {lang === 'EN' ? `Towards ${activeTrain.dest}` : `${activeTrain.destHi} की ओर`}
              </span>
            </div>

            {/* Platform Badge */}
            <div className="flex flex-col items-start sm:items-end">
              <span className="text-[10px] uppercase tracking-widest text-[#6B7480]">
                {lang === 'EN' ? 'Berthing Platform' : 'प्लेटफ़ॉर्म'}
              </span>
              <div className="text-3xl sm:text-5xl font-bold text-[#E9EBEE] bg-[#0A0B0D] px-4 py-1 border border-[#23272F] rounded-sm mt-1">
                PF-{activeTrain.platform}
              </div>
            </div>
          </div>

          {/* Giant Arrival Window Display */}
          <div className="py-4 text-center sm:text-left">
            <span className="text-xs uppercase tracking-widest text-[#6B7480] block mb-1">
              {lang === 'EN' ? 'CALIBRATED EXPECTED ARRIVAL' : 'अनुमानित आगमन समय'}
            </span>

            {/* Giant 72px–96px Mono Arrival */}
            <div className="text-6xl sm:text-8xl lg:text-9xl font-bold text-[#F5A524] tracking-tight tabular-nums font-mono">
              {activeTrain.expected}
            </div>

            {/* Signal Blue Confidence Window */}
            <div className="inline-flex items-center gap-2 px-3 py-1.5 mt-3 bg-[rgba(108,159,255,0.13)] border border-[#6C9FFF]/40 text-[#6C9FFF] rounded-sm text-sm sm:text-base font-semibold">
              <span className="w-2 h-2 rounded-full bg-[#6C9FFF]" />
              <span>
                {lang === 'EN' ? 'Window: between' : 'अनुमानित अंतराल:'}{' '}
                <span className="font-bold">{activeTrain.rangeStart}</span> –{' '}
                <span className="font-bold">{activeTrain.rangeEnd}</span>
              </span>
            </div>
          </div>

          {/* Aspect Status & Plain-Language Reason Card */}
          <div className="p-4 bg-[#0A0B0D] border border-[#23272F] rounded-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <AspectLamp
                  aspect={aspect}
                  label={
                    activeTrain.delayMin <= 0
                      ? lang === 'EN' ? 'ON TIME' : 'समय पर'
                      : lang === 'EN' ? `ABOUT ${activeTrain.delayMin} MIN LATE` : `लगभग ${activeTrain.delayMin} मिनट विलंब`
                  }
                  size="md"
                />
              </div>
              <p className="text-xs sm:text-sm font-sans text-[#A3ABB6] mt-0.5">
                {lang === 'EN' ? activeTrain.reason : activeTrain.reasonHi}
              </p>
            </div>

            <div className="text-right shrink-0">
              <span className="text-xs font-bold text-[#3DDC97]">
                {activeTrain.minAway} min away from station
              </span>
            </div>
          </div>
        </div>
      </main>

      {/* Footer Provenance Ribbon */}
      <footer className="border-t border-[#23272F] pt-4">
        <Provenance
          updatedAt={dataUpdatedAt}
          source="RAILTWIN-X PUBLIC PASSENGER TELEMETRY STREAM"
        />
      </footer>
    </div>
  );
}
