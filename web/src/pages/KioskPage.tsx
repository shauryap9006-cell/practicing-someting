import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useConnectionState } from '../lib/api';

interface StationBlock {
  train_no: string;
  train_name: string;
  train_class?: string;
  platform: number | string;
  start_time: string;
  end_time: string;
  dwell_min: number;
  is_conflicted?: boolean;
}

interface StationInfo {
  code: string;
  name: string;
  fullName: string;
  division?: string;
  platformsCount?: number;
}

export const KioskPage: React.FC = () => {
  const [stationCode, setStationCode] = useState<string>('NDLS');
  const [stationInfo, setStationInfo] = useState<StationInfo | null>(null);
  const [blocks, setBlocks] = useState<StationBlock[]>([]);
  const [loading, setLoading] = useState(true);
  const [istTime, setIstTime] = useState<string>('');
  const [lang, setLang] = useState<'EN' | 'HI'>('EN');
  const connection = useConnectionState();

  const stations = [
    { code: 'NDLS', name: 'New Delhi', nameHi: 'नई दिल्ली' },
    { code: 'CNB', name: 'Kanpur Central', nameHi: 'कानपुर सेंट्रल' },
    { code: 'PRYJ', name: 'Prayagraj Jn', nameHi: 'प्रयागराज जंक्शन' },
    { code: 'DDU', name: 'Pt Deen Dayal', nameHi: 'पं. दीन दयाल उपाध्याय' },
  ];

  // Live IST Clock
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const formatted = new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Asia/Kolkata',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      }).format(now);
      setIstTime(formatted);
    };

    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  // Auto-cycle language every 8 seconds (authentic IR PIDS behavior)
  useEffect(() => {
    const langTimer = setInterval(() => {
      setLang((prev) => (prev === 'EN' ? 'HI' : 'EN'));
    }, 8000);
    return () => clearInterval(langTimer);
  }, []);

  const loadStationData = useCallback(async (code: string) => {
    setLoading(true);
    try {
      const [infoRes, ganttRes] = await Promise.all([
        fetch(`/v1/stations/${code}`).then((r) => r.json()),
        fetch(`/v1/stations/${code}/gantt`).then((r) => r.json()),
      ]);

      setStationInfo(infoRes);
      setBlocks(ganttRes.blocks || []);
    } catch {
      // Keep existing on error
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStationData(stationCode);
    const interval = setInterval(() => loadStationData(stationCode), 20000);
    return () => clearInterval(interval);
  }, [stationCode, loadStationData]);

  const currentStation = stations.find((s) => s.code === stationCode) || stations[0];

  const formatTime = (isoString: string) => {
    if (!isoString) return '--:--';
    if (isoString.includes('T')) {
      return isoString.split('T')[1]?.slice(0, 5) || '--:--';
    }
    return isoString.slice(0, 5);
  };

  const nextTrain = blocks[0];

  return (
    <div className="min-h-screen bg-[#12110E] text-[#F3EFE6] flex flex-col justify-between font-sans select-none antialiased">
      {/* Top Kiosk Masthead Bar */}
      <header className="bg-[#1C1A14] border-b border-[#38332A] px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link
            to="/t"
            className="font-mono text-xs text-[#A8A194] hover:text-[#F3EFE6] border border-[#38332A] px-2.5 py-1 rounded bg-[#24211A] transition-colors"
          >
            ← EXIT KIOSK
          </Link>

          <div className="flex flex-col">
            <span className="font-mono text-xs uppercase tracking-widest text-[#E6A100] font-bold">
              INDIAN RAILWAYS · PASSENGER INFORMATION DISPLAY SYSTEM (PIDS)
            </span>
            <div className="flex items-baseline gap-2">
              <h1 className="font-serif text-2xl font-bold text-[#FDFCF8] tracking-tight">
                {lang === 'HI' ? currentStation.nameHi : currentStation.name}
              </h1>
              <span className="font-mono text-sm text-[#A8A194] font-semibold">
                ({currentStation.code})
              </span>
            </div>
          </div>
        </div>

        {/* Live IST Clock & Station Selector */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-[#A8A194] uppercase">Station:</span>
            <select
              value={stationCode}
              onChange={(e) => setStationCode(e.target.value)}
              className="bg-[#24211A] border border-[#38332A] text-[#FDFCF8] font-mono text-xs px-2.5 py-1 rounded cursor-pointer"
            >
              {stations.map((s) => (
                <option key={s.code} value={s.code}>
                  {s.code} - {s.name}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            onClick={() => setLang((prev) => (prev === 'EN' ? 'HI' : 'EN'))}
            className="font-mono text-xs px-3 py-1 bg-[#24211A] border border-[#E6A100]/40 text-[#E6A100] rounded font-semibold hover:bg-[#E6A100]/10 transition-colors cursor-pointer"
          >
            {lang === 'EN' ? 'हिंदी में देखें' : 'VIEW IN ENGLISH'}
          </button>

          <div className="flex flex-col items-end">
            <span className="font-mono text-[10px] uppercase tracking-wider text-[#A8A194]">
              INDIAN STANDARD TIME
            </span>
            <span className="font-mono text-2xl sm:text-3xl font-bold tabular-nums text-[#FDFCF8]">
              {istTime || '--:--:--'}
            </span>
          </div>
        </div>
      </header>

      {/* Hero Next Approaching Train Banner */}
      {nextTrain && (
        <div className="bg-[#191712] border-b border-[#38332A] px-6 py-6 flex flex-wrap items-center justify-between gap-6">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2 font-mono text-xs text-[#E6A100] font-bold">
              <span className="w-2.5 h-2.5 rounded-[2px] bg-[#E6A100] animate-ping" />
              <span>{lang === 'HI' ? 'अगली आने वाली गाड़ी' : 'NEXT APPROACHING SERVICE'}</span>
            </div>
            <div className="flex flex-wrap items-baseline gap-3">
              <span className="font-mono text-3xl font-bold text-[#FDFCF8]">
                #{nextTrain.train_no}
              </span>
              <span className="font-serif text-2xl font-bold text-[#FDFCF8]">
                {nextTrain.train_name}
              </span>
            </div>
            <span className="font-mono text-xs text-[#A8A194]">
              {lang === 'HI' ? 'स्टॉप ठहराव' : 'Station Dwell'}: {nextTrain.dwell_min} min · Dynamic twin ETA
            </span>
          </div>

          <div className="flex items-center gap-8">
            <div className="flex flex-col items-end">
              <span className="font-mono text-xs uppercase text-[#A8A194]">
                {lang === 'HI' ? 'अपेक्षित आगमन' : 'EXPECTED ARRIVAL'}
              </span>
              <span className="font-mono text-4xl sm:text-5xl font-bold text-[#E6A100] tabular-nums">
                {formatTime(nextTrain.start_time)}
              </span>
            </div>

            <div className="flex flex-col items-center justify-center px-5 py-3 bg-[#E6A100] text-[#191712] rounded-[3px]">
              <span className="font-mono text-[10px] uppercase font-bold tracking-wider">
                {lang === 'HI' ? 'प्लेटफॉर्म' : 'PLATFORM'}
              </span>
              <span className="font-mono text-3xl sm:text-4xl font-black tabular-nums">
                {nextTrain.platform || '1'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Main Timetable Board */}
      <main className="flex-1 p-6 overflow-x-auto">
        <table className="w-full text-left border-collapse text-sm">
          <thead>
            <tr className="border-b-2 border-[#38332A] text-[#A8A194] font-mono text-xs uppercase">
              <th className="py-3 px-4">{lang === 'HI' ? 'गाड़ी सं.' : 'TRAIN NO'}</th>
              <th className="py-3 px-4">{lang === 'HI' ? 'गाड़ी का नाम' : 'SERVICE NAME'}</th>
              <th className="py-3 px-4 text-center">{lang === 'HI' ? 'प्लेटफॉर्म' : 'PF'}</th>
              <th className="py-3 px-4 text-right">{lang === 'HI' ? 'निर्धारित' : 'SCHED'}</th>
              <th className="py-3 px-4 text-right text-[#E6A100] font-bold">{lang === 'HI' ? 'अनुमानित' : 'EXPECTED'}</th>
              <th className="py-3 px-4 text-right">{lang === 'HI' ? 'स्थिति' : 'STATUS'}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#2A261F] font-mono">
            {loading && blocks.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-[#A8A194] text-sm">
                  Loading live station PIDS board...
                </td>
              </tr>
            ) : blocks.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-[#A8A194] text-sm">
                  No upcoming services registered at this station.
                </td>
              </tr>
            ) : (
              blocks.slice(0, 12).map((block, idx) => (
                <tr key={`${block.train_no}-${idx}`} className="hover:bg-[#1E1B15] transition-colors">
                  <td className="py-3.5 px-4 font-bold text-base text-[#FDFCF8] tabular-nums">
                    #{block.train_no}
                  </td>
                  <td className="py-3.5 px-4 font-sans font-semibold text-base text-[#FDFCF8]">
                    {block.train_name}
                  </td>
                  <td className="py-3.5 px-4 text-center">
                    <span className="font-bold text-base px-3 py-1 bg-[#28241D] border border-[#443E33] rounded text-[#E6A100] tabular-nums inline-block min-w-[36px]">
                      {block.platform || '1'}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right text-[#A8A194] text-base tabular-nums">
                    {formatTime(block.start_time)}
                  </td>
                  <td className="py-3.5 px-4 text-right font-bold text-lg text-[#E6A100] tabular-nums">
                    {formatTime(block.start_time)}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <span className="text-xs px-2 py-0.5 rounded border border-[#1B6B3A]/40 bg-[#1B6B3A]/10 text-[#4ADE80] font-bold">
                      RIGHT TIME
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </main>

      {/* Footer Disclaimer & Offline Lamp */}
      <footer className="bg-[#181611] border-t border-[#38332A] px-6 py-3 flex flex-wrap items-center justify-between text-xs font-mono text-[#A8A194]">
        <div className="flex items-center gap-2">
          <span
            className={`w-2.5 h-2.5 rounded-[2px] ${
              connection.status === 'LIVE' ? 'bg-[#1B6B3A]' : 'bg-[#B3362B]'
            }`}
          />
          <span>
            {connection.status === 'LIVE'
              ? 'PIDS Telemetry Feed Live · Auto-Syncing'
              : 'PIDS Standby Mode · Reconnecting'}
          </span>
        </div>

        <span>
          Dynamic ETA Twin powered by RailTwin-X v4 · Dedicated Passenger Kiosk Mode
        </span>
      </footer>
    </div>
  );
};
