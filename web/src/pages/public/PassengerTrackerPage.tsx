import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useParams, useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api, PassengerSnapshot } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { AspectLamp, AspectType } from '@/components/aspect';
import { useTrackModal } from '@/context/TrackModalContext';
import { useLiveMotionEngine } from '@/lib/useLiveMotionEngine';
import {
  Clock,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Share2,
  RefreshCw,
  Languages,
  Check,
  Bell,
  BellRing,
  Search,
  X,
  Compass,
  ArrowDown,
  LocateFixed,
} from 'lucide-react';

function formatStationName(name: string): string {
  return name
    .replace(/ Junction$/i, ' Jn')
    .replace(/ Junction /gi, ' Jn ')
    .replace(/ Central$/i, ' Central');
}

export function PassengerTrackerPage() {
  const { trainNo: routeTrainNo } = useParams<{ trainNo?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { openModal, lang, setLang } = useTrackModal();

  const stopParam = searchParams.get('stop') || undefined;
  const pnrParam = searchParams.get('pnr') || undefined;

  const [selectedStopCode, setSelectedStopCode] = useState<string | undefined>(stopParam);
  const [whyExpanded, setWhyExpanded] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [showAlarmModal, setShowAlarmModal] = useState(false);

  // Train DOM Ref for Auto-Centering
  const trainMarkerRef = useRef<HTMLDivElement | null>(null);
  const hasAutoCenteredRef = useRef<boolean>(false);

  // Stale & Offline Connection Tracking
  const [lastFetchTime, setLastFetchTime] = useState<number>(Date.now());
  const [secondsSinceUpdate, setSecondsSinceUpdate] = useState<number>(0);
  const [isStale, setIsStale] = useState<boolean>(false);
  const [isConnectionOffline, setIsConnectionOffline] = useState<boolean>(!navigator.onLine);

  const { data: initialPopular } = useQuery({
    queryKey: ['passenger-popular-init'],
    queryFn: () => api.getPopularPassengerTrains(),
    enabled: !routeTrainNo && !pnrParam,
    staleTime: 60000,
  });

  const activeTrainNo =
    routeTrainNo ||
    (!pnrParam && initialPopular && initialPopular.length > 0
      ? initialPopular[0].train_no
      : undefined);

  // Single Source of Truth snapshot fetch
  const {
    data: snapshot,
    isLoading: isSnapshotLoading,
    isError: isSnapshotError,
    error: snapshotError,
    refetch,
  } = useQuery<PassengerSnapshot>({
    queryKey: ['passenger-snapshot', activeTrainNo, selectedStopCode, pnrParam],
    queryFn: async () => {
      const data = await api.getPassengerSnapshot(activeTrainNo, selectedStopCode, pnrParam);
      setLastFetchTime(Date.now());
      setSecondsSinceUpdate(0);
      setIsStale(false);
      return data;
    },
    enabled: !!activeTrainNo || !!pnrParam,
    refetchInterval: (query) => {
      if (
        query.state.data?.train.run_status === 'COMPLETED' ||
        query.state.data?.train.run_status === 'NOT_RUNNING_TODAY'
      ) {
        return false;
      }
      return 5000;
    },
    placeholderData: (previousData) => previousData,
    staleTime: 4000,
  });

  const isCompleted = snapshot?.train.run_status === 'COMPLETED';
  const isNotRunningToday = snapshot?.train.run_status === 'NOT_RUNNING_TODAY';

  // Client Live Motion Engine (Layer 2, 3 & 4)
  const motion = useLiveMotionEngine({
    trainNo: activeTrainNo,
    snapshot,
    selectedStopCode,
    isCompleted,
    isNotRunningToday,
    refetchSnapshot: refetch,
  });

  // Elapsed seconds timer
  useEffect(() => {
    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - lastFetchTime) / 1000);
      setSecondsSinceUpdate(elapsed);
      if (elapsed >= 10 && !isStale) {
        setIsStale(true);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [lastFetchTime, isStale]);

  // Online / Offline event listeners
  useEffect(() => {
    const handleOnline = () => {
      setIsConnectionOffline(false);
      refetch();
    };
    const handleOffline = () => {
      setIsConnectionOffline(true);
    };
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [refetch]);

  // Auto-Center Train on Screen when mounted
  useEffect(() => {
    if (snapshot && !hasAutoCenteredRef.current && trainMarkerRef.current) {
      hasAutoCenteredRef.current = true;
      setTimeout(() => {
        trainMarkerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 400);
    }
  }, [snapshot]);

  // Handler to manually center train
  const scrollToTrain = () => {
    if (trainMarkerRef.current) {
      trainMarkerRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  // Tab title & favicon
  useEffect(() => {
    if (snapshot) {
      const expectedTime = snapshot.selected_stop.expected_arr;
      const trainCode = snapshot.train.train_no;
      document.title = `${expectedTime} · ${trainCode} | Where Is My Train`;
    }
  }, [snapshot]);

  // SVG Speed Sparkline from last 30 speed values (TOP LEVEL HOOK)
  const sparklineSvg = useMemo(() => {
    const history = motion.speedHistory;
    if (!history || history.length < 2) return null;
    const minS = Math.min(...history, 60);
    const maxS = Math.max(...history, 130);
    const range = Math.max(10, maxS - minS);
    const width = 64;
    const height = 18;

    const points = history
      .map((val, idx) => {
        const x = (idx / (history.length - 1)) * width;
        const y = height - ((val - minS) / range) * (height - 4) - 2;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');

    return (
      <svg width={width} height={height} className="overflow-visible shrink-0 opacity-80">
        <polyline fill="none" stroke="#22C55E" strokeWidth="1.5" points={points} />
      </svg>
    );
  }, [motion.speedHistory]);

  const handleStopSelect = (code: string) => {
    setSelectedStopCode(code);
    const newParams = new URLSearchParams(searchParams);
    newParams.set('stop', code);
    setSearchParams(newParams);
  };

  const handleCopyShare = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  // Loading Skeleton
  if (isSnapshotLoading && !snapshot) {
    return (
      <div className="min-h-screen bg-[#08090B] text-[#E2E8F0] font-sans p-4 max-w-md mx-auto space-y-3">
        <div className="h-14 bg-[#12151B] rounded animate-pulse" />
        <div className="h-28 bg-[#12151B] rounded animate-pulse" />
        <div className="h-[500px] bg-[#12151B] rounded animate-pulse" />
      </div>
    );
  }

  // Error fallback
  if (isSnapshotError || !snapshot) {
    return (
      <div className="min-h-screen bg-[#08090B] text-[#E2E8F0] font-sans p-4 max-w-md mx-auto flex flex-col items-center justify-center min-h-[70vh] text-center space-y-4">
        <div className="w-12 h-12 rounded-full bg-[#EF4444]/10 border border-[#EF4444]/30 flex items-center justify-center text-[#EF4444]">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <h2 className="text-base font-bold text-[#F8FAFC]">
            {lang === 'HI' ? 'ट्रेन विवरण उपलब्ध नहीं है' : 'Train Details Unavailable'}
          </h2>
          <p className="text-xs text-[#94A3B8] max-w-xs font-mono">
            {lang === 'HI'
              ? 'कृपया ट्रेन नंबर या PNR की जांच करें और पुनः प्रयास करें।'
              : 'Please check the train number or PNR and try again.'}
          </p>
        </div>
        <div className="flex items-center gap-2 pt-2">
          <button
            type="button"
            onClick={() => refetch()}
            className="px-4 py-2 bg-[#161A22] hover:bg-[#1E232E] border border-[#2A313D] rounded text-xs font-mono text-[#F8FAFC] flex items-center gap-2 min-h-[44px]"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{lang === 'HI' ? 'पुनः प्रयास करें' : 'Retry'}</span>
          </button>
          <button
            type="button"
            onClick={(e) => openModal(undefined, e.currentTarget)}
            className="px-4 py-2 bg-[#F59E0B] hover:bg-[#F59E0B]/90 text-[#08090B] rounded text-xs font-mono font-bold flex items-center gap-2 min-h-[44px]"
          >
            <Search className="w-3.5 h-3.5" />
            <span>{lang === 'HI' ? 'ट्रेन खोजें' : 'Search Train'}</span>
          </button>
        </div>
      </div>
    );
  }

  const {
    train,
    next_stop,
    selected_stop,
    single_delay,
    autopsy,
    all_stops,
    waypoints = [],
    provenance,
  } = snapshot;

  const aspectColor =
    single_delay.status_lamp === 'green'
      ? '#22C55E'
      : single_delay.status_lamp === 'amber'
      ? '#F59E0B'
      : '#EF4444';

  const lampAspect: AspectType =
    single_delay.status_lamp === 'green'
      ? 'clear'
      : single_delay.status_lamp === 'amber'
      ? 'caution'
      : 'restrict';

  const currentDrKm = motion.drKm;

  return (
    <div
      className={`min-h-screen bg-[#08090B] text-[#E2E8F0] font-sans pb-20 transition-opacity duration-200 ${
        isConnectionOffline || isStale ? 'opacity-90' : 'opacity-100'
      }`}
    >
      <SEO
        title={`${selected_stop.expected_arr} · ${train.train_no} ${train.name} | Live Where Is My Train`}
        description={`Track ${train.train_no} ${train.name} live with continuous 60fps dead-reckoning, station platforms, and accurate timetable tracking.`}
      />

      {/* ========================================================================= */}
      {/* 1. COMPACT RAILWAY COMMAND HEADER (WHERE IS MY TRAIN STYLE)                */}
      {/* ========================================================================= */}
      <header className="sticky top-0 z-40 bg-[#0E1117]/95 backdrop-blur-md border-b border-[#1E232E] shadow-lg">
        {/* Top Navbar */}
        <div className="max-w-2xl mx-auto px-3 sm:px-4 py-1.5 flex items-center justify-between border-b border-[#1A1E27]">
          <div className="flex items-center gap-2">
            <Link to="/" className="font-mono text-xs font-bold tracking-tight text-[#F8FAFC]">
              RAILTWIN<span className="text-[#F59E0B]">-X</span>
            </Link>

            {/* Live 60fps Connection Pill */}
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[#141820] border border-[#232A36] text-[10px] font-mono">
              {isConnectionOffline ? (
                <>
                  <span className="w-1.5 h-1.5 rounded-full bg-[#EF4444]" />
                  <span className="text-[#EF4444] font-bold">OFFLINE</span>
                </>
              ) : isStale ? (
                <>
                  <span className="w-1.5 h-1.5 rounded-full bg-[#F59E0B] animate-pulse" />
                  <span className="text-[#F59E0B] font-bold">STALE ({secondsSinceUpdate}s)</span>
                </>
              ) : (
                <>
                  <span className="w-1.5 h-1.5 rounded-full bg-[#22C55E] shadow-[0_0_6px_rgba(34,197,94,0.7)] animate-pulse" />
                  <span className="text-[#22C55E] font-bold">LIVE 60FPS</span>
                </>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {/* Station Alarm Button */}
            <button
              type="button"
              onClick={() => setShowAlarmModal(true)}
              className={`px-2 py-1 rounded text-xs font-mono flex items-center gap-1 transition-colors min-h-[32px] border ${
                motion.alarmEnabled
                  ? 'bg-[#22C55E]/15 border-[#22C55E]/40 text-[#22C55E]'
                  : 'bg-[#141820] hover:bg-[#1C222D] border-[#232A36] text-[#94A3B8]'
              }`}
              title="Station Arrival Alarm"
            >
              {motion.alarmEnabled ? (
                <BellRing className="w-3.5 h-3.5 text-[#22C55E] animate-pulse" />
              ) : (
                <Bell className="w-3.5 h-3.5" />
              )}
              <span className="hidden sm:inline">
                {motion.alarmEnabled ? `${motion.alarmThresholdMin}m Alarm` : 'Alarm'}
              </span>
            </button>

            {/* Language EN / HI Toggle */}
            <button
              type="button"
              onClick={() => setLang(lang === 'EN' ? 'HI' : 'EN')}
              className="px-2 py-1 bg-[#141820] hover:bg-[#1C222D] border border-[#232A36] rounded text-xs font-mono text-[#F8FAFC] flex items-center gap-1 transition-colors min-h-[32px]"
              aria-label="Toggle language"
            >
              <Languages className="w-3.5 h-3.5 text-[#F59E0B]" />
              <span>{lang === 'EN' ? 'हिंदी' : 'EN'}</span>
            </button>

            {/* Search Modal Trigger */}
            <button
              type="button"
              onClick={(e) => openModal(undefined, e.currentTarget)}
              className="px-2.5 py-1 bg-[#F59E0B] hover:bg-[#F59E0B]/90 text-[#08090B] font-mono font-bold text-xs rounded transition-colors flex items-center gap-1 min-h-[32px]"
            >
              <span>🚆</span>
              <span className="hidden sm:inline">{lang === 'HI' ? 'खोजें' : 'Search'}</span>
            </button>
          </div>
        </div>

        {/* Train Identity & Delay Strip */}
        <div className="max-w-2xl mx-auto px-3 sm:px-4 py-2 flex items-center justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-base font-bold text-[#F8FAFC]">
                {train.train_no}
              </span>
              <span className="text-xs sm:text-sm font-semibold text-[#F8FAFC] truncate">
                {lang === 'HI' ? train.name_hi : train.name}
              </span>
            </div>
            <div className="text-[11px] font-mono text-[#94A3B8] flex items-center gap-1.5">
              <span>{lang === 'HI' ? train.origin.name_hi : train.origin.name}</span>
              <span>→</span>
              <span>{lang === 'HI' ? train.destination.name_hi : train.destination.name}</span>
            </div>
          </div>

          {/* Status Aspect Pill */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#141820] border border-[#232A36] shrink-0">
            <AspectLamp aspect={lampAspect} size="sm" />
            <span className="text-xs font-mono font-bold" style={{ color: aspectColor }}>
              {isCompleted
                ? 'Arrived ✓'
                : lang === 'HI'
                ? single_delay.label_hi
                : single_delay.label}
            </span>
          </div>
        </div>

        {/* Live Telemetry Bar */}
        <div className="bg-[#12151B] border-t border-[#1E232E] px-3 sm:px-4 py-1.5 text-xs font-mono flex items-center justify-between gap-2">
          {/* Next Halt & Speed */}
          <div className="flex items-center gap-2.5 min-w-0">
            {next_stop && !isCompleted ? (
              <div className="flex items-center gap-1.5 text-[#22C55E] truncate">
                <span className="relative flex h-2 w-2 shrink-0">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#22C55E] opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-[#22C55E]" />
                </span>
                <span className="font-bold shrink-0">Next: {next_stop.station_code}</span>
                <span className="text-[#64748B]">·</span>
                <span className="text-[#CBD5E1] truncate">{next_stop.km_away} km ({next_stop.expected_time})</span>
              </div>
            ) : (
              <span className="text-[#94A3B8]">Destination Reached</span>
            )}

            <div className="hidden sm:flex items-center gap-1.5 pl-2 border-l border-[#232A36]">
              {sparklineSvg}
              <span className="text-[#22C55E] font-bold tabular-nums">
                {Math.round(motion.displaySpeed)} km/h
              </span>
            </div>
          </div>

          {/* Odometer & Destination Selector Chip */}
          <div className="flex items-center gap-1.5 shrink-0">
            <span className="px-1.5 py-0.5 bg-[#181D26] border border-[#2A313D] rounded text-[11px] font-bold text-[#F8FAFC] tabular-nums">
              {motion.odometerKm}
            </span>

            <div className="relative">
              <select
                value={selected_stop.station_code}
                onChange={(e) => handleStopSelect(e.target.value)}
                className="appearance-none bg-[#181D26] hover:bg-[#202632] border border-[#2A313D] rounded px-2 py-0.5 pr-5 text-[11px] font-mono text-[#F59E0B] font-bold focus:outline-none focus:border-[#F59E0B] cursor-pointer transition-colors"
                aria-label="Change destination stop"
              >
                {all_stops.map((s: any) => (
                  <option key={s.station_code} value={s.station_code}>
                    To: {s.station_code} ({s.predicted_arr || s.predicted_dep})
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3 h-3 text-[#94A3B8] absolute right-1 top-1.5 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Sticky Approach Banner */}
        {motion.isApproachingStop && !isCompleted && (
          <div className="bg-gradient-to-r from-[#F59E0B] via-[#FBBF24] to-[#F59E0B] text-[#08090B] font-mono px-3 py-1 text-xs font-bold flex items-center justify-between shadow-md">
            <div className="flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 animate-bounce shrink-0" />
              <span className="truncate">
                {lang === 'HI'
                  ? `शीघ्र आगमन — ${selected_stop.station_name_hi} पर उतरने की तैयारी करें!`
                  : `ARRIVING SOON — ${selected_stop.station_name} (${motion.distToStopKm} km away)`}
              </span>
            </div>
            <span className="text-[11px] bg-[#08090B]/20 px-2 py-0.5 rounded shrink-0">
              Platform {selected_stop.platform || 'TBA'}
            </span>
          </div>
        )}
      </header>

      {/* WAYPOINT PASS TOAST */}
      {motion.activeCrossingToast && (
        <aside
          aria-label="Waypoint Crossing Notification"
          className="fixed bottom-20 right-4 z-50 bg-[#12151B] border-2 border-[#22C55E] rounded-lg p-3 shadow-2xl max-w-xs flex items-start gap-2.5 animate-in fade-in slide-in-from-bottom-3 duration-200"
        >
          <div className="w-6 h-6 rounded-full bg-[#22C55E]/20 flex items-center justify-center text-[#22C55E] shrink-0 mt-0.5">
            <Check className="w-3.5 h-3.5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[11px] font-mono font-bold text-[#F8FAFC] flex items-center gap-1">
              <span>{lang === 'HI' ? 'पार किया' : 'Crossed'}</span>
              <span className="text-[#64748B]">·</span>
              <span className="text-[#22C55E]">{motion.activeCrossingToast.timeStr}</span>
            </div>
            <div className="text-xs font-semibold text-[#F8FAFC] truncate">
              {lang === 'HI' && motion.activeCrossingToast.waypointNameHi
                ? motion.activeCrossingToast.waypointNameHi
                : motion.activeCrossingToast.waypointName}
            </div>
            <div className="text-[10px] font-mono text-[#94A3B8]">
              {motion.activeCrossingToast.status === 'on_schedule'
                ? 'On schedule'
                : `+${motion.activeCrossingToast.delayMin}m late`}
            </div>
          </div>
          <button
            type="button"
            onClick={motion.dismissCrossingToast}
            className="text-[#64748B] hover:text-[#F8FAFC] p-1"
          >
            <X className="w-3 h-3" />
          </button>
        </aside>
      )}

      {/* STATION ALARM MODAL */}
      {showAlarmModal && (
        <div className="fixed inset-0 z-50 bg-[#08090B]/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#12151B] border border-[#232A36] rounded-lg max-w-sm w-full p-4 space-y-3 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#232A36] pb-2">
              <div className="flex items-center gap-2 text-sm font-mono font-bold text-[#F8FAFC]">
                <BellRing className="w-4 h-4 text-[#F59E0B]" />
                <span>{lang === 'HI' ? 'स्टेशन आगमन अलार्म' : 'Station Arrival Alarm'}</span>
              </div>
              <button
                type="button"
                onClick={() => setShowAlarmModal(false)}
                className="text-[#94A3B8] hover:text-[#F8FAFC] p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-[#94A3B8]">
              We will wake you up with a railway chime when the train is approaching {selected_stop.station_name}.
            </p>

            <div className="space-y-1.5 font-mono text-xs">
              <span className="text-[#64748B]">Alert Me Before Arrival:</span>
              <div className="grid grid-cols-3 gap-2">
                {[5, 10, 15].map((mins) => (
                  <button
                    key={mins}
                    type="button"
                    onClick={() => motion.setAlarmThresholdMin(mins)}
                    className={`p-2 rounded border text-center font-bold transition-colors ${
                      motion.alarmThresholdMin === mins
                        ? 'bg-[#F59E0B]/20 border-[#F59E0B] text-[#F59E0B]'
                        : 'bg-[#181D26] border-[#2A313D] text-[#94A3B8]'
                    }`}
                  >
                    {mins} mins
                  </button>
                ))}
              </div>
            </div>

            <button
              type="button"
              onClick={async () => {
                await motion.toggleAlarm(!motion.alarmEnabled);
                setShowAlarmModal(false);
              }}
              className={`w-full py-2 rounded text-xs font-mono font-bold flex items-center justify-center gap-2 transition-colors ${
                motion.alarmEnabled
                  ? 'bg-[#EF4444]/20 border border-[#EF4444]/50 text-[#EF4444]'
                  : 'bg-[#F59E0B] text-[#08090B]'
              }`}
            >
              {motion.alarmEnabled ? 'Disable Alarm' : 'Set Arrival Alarm'}
            </button>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 2. THE FULL-BLEED VERTICAL RAILWAY TRACK TIMELINE (WHERE IS MY TRAIN)      */}
      {/* ========================================================================= */}
      <main className="max-w-2xl mx-auto px-3 sm:px-4 pt-2">
        {/* Route Table Header */}
        <div className="flex items-center justify-between pb-1.5 text-[10px] font-mono text-[#64748B] border-b border-[#1E232E]">
          <div className="flex items-center gap-2 pl-1">
            <span>TIME</span>
            <span>·</span>
            <span>STATION</span>
          </div>
          <div className="flex items-center gap-3 pr-1">
            <span>PLATFORM</span>
            <span>·</span>
            <span>DISTANCE</span>
          </div>
        </div>

        {/* CONTINUOUS VERTICAL RAILWAY TRACK */}
        <div className="relative py-1">
          {all_stops.map((stn: any, idx: number) => {
            const isSelected = stn.station_code === selected_stop.station_code;
            const isPassed = stn.status === 'passed';
            const isNext = stn.is_next_stop;
            const isLast = idx === all_stops.length - 1;

            const nextStn = !isLast ? all_stops[idx + 1] : null;
            const isActiveSegment =
              !isCompleted &&
              nextStn &&
              currentDrKm >= stn.distance_km &&
              currentDrKm <= nextStn.distance_km;

            // Fractional distance along this active segment (0 to 1)
            const segProgress =
              isActiveSegment && nextStn
                ? Math.max(0.08, Math.min(0.92, (currentDrKm - stn.distance_km) / (nextStn.distance_km - stn.distance_km)))
                : 0;

            const segmentWaypoints = nextStn
              ? waypoints.filter((w: any) => w.km > stn.distance_km && w.km < nextStn.distance_km)
              : [];

            const displayName = formatStationName(stn.station_name);

            return (
              <div key={stn.station_code} className="relative">
                {/* STATION ROW */}
                <div
                  onClick={() => handleStopSelect(stn.station_code)}
                  className={`flex items-center py-2.5 px-1.5 rounded cursor-pointer transition-colors ${
                    isNext
                      ? 'bg-[#22C55E]/10'
                      : isSelected
                      ? 'bg-[#F59E0B]/10'
                      : 'hover:bg-[#12151B]'
                  }`}
                >
                  {/* Left Column: Arrival Times (Width: 56px) */}
                  <div className="w-14 sm:w-16 text-left font-mono shrink-0">
                    <div className="text-[10px] text-[#64748B] line-through">
                      {stn.scheduled_arr || stn.scheduled_dep}
                    </div>
                    <div
                      className={`text-xs sm:text-sm font-bold tabular-nums leading-tight ${
                        isPassed
                          ? 'text-[#94A3B8]'
                          : isNext
                          ? 'text-[#22C55E]'
                          : isSelected
                          ? 'text-[#F59E0B]'
                          : 'text-[#F8FAFC]'
                      }`}
                    >
                      {stn.predicted_arr || stn.predicted_dep}
                    </div>
                    {stn.actual_arr ? (
                      <div className="text-[9px] text-[#22C55E] font-medium">
                        Arr {stn.actual_arr}
                      </div>
                    ) : isNext ? (
                      <div className="text-[9px] text-[#22C55E] font-bold">
                        ~{next_stop?.eta_minutes}m away
                      </div>
                    ) : null}
                  </div>

                  {/* Center Column: Railway Track Node Icon */}
                  <div className="relative flex items-center justify-center w-7 shrink-0 z-10">
                    <div
                      className={`w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center transition-all ${
                        isNext
                          ? 'bg-[#22C55E] border-[#F8FAFC] ring-4 ring-[#22C55E]/40 scale-125'
                          : isSelected
                          ? 'bg-[#F59E0B] border-[#F8FAFC] ring-4 ring-[#F59E0B]/30 scale-110'
                          : isPassed
                          ? 'bg-[#22C55E] border-[#22C55E]'
                          : 'bg-[#08090B] border-[#2A313D]'
                      }`}
                    >
                      {isPassed && <Check className="w-2 h-2 text-[#08090B]" />}
                      {isSelected && !isPassed && <span className="w-1 h-1 rounded-full bg-[#08090B]" />}
                    </div>
                  </div>

                  {/* Right Column: Station Details */}
                  <div className="flex-1 min-w-0 pl-2 flex items-center justify-between gap-1.5">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline gap-1.5 truncate">
                        <span className="font-mono text-xs sm:text-sm font-bold text-[#F8FAFC] truncate">
                          {displayName}
                        </span>
                        <span className="text-[10px] font-mono text-[#64748B] shrink-0">
                          ({stn.station_code})
                        </span>
                        {isNext && (
                          <span className="px-1 py-0.2 bg-[#22C55E] text-[#08090B] font-mono text-[9px] font-bold rounded shrink-0">
                            NEXT
                          </span>
                        )}
                        {isSelected && !isNext && (
                          <span className="px-1 py-0.2 bg-[#F59E0B]/20 border border-[#F59E0B]/40 text-[#F59E0B] font-mono text-[9px] font-bold rounded shrink-0">
                            MY STOP
                          </span>
                        )}
                      </div>
                      <div className="text-[10px] text-[#64748B] truncate">
                        {lang === 'HI' ? stn.station_name_hi : ''}
                      </div>
                    </div>

                    {/* Platform & Distance Pills on Far Right */}
                    <div className="flex items-center gap-1.5 font-mono shrink-0">
                      <span className="px-1.5 py-0.5 bg-[#141820] border border-[#232A36] rounded text-[10px] font-bold text-[#CBD5E1]">
                        {stn.platform ? `PF ${stn.platform}` : 'PF —'}
                      </span>
                      <span className="text-[10px] text-[#64748B] w-10 text-right">
                        {stn.distance_km}km
                      </span>
                    </div>
                  </div>
                </div>

                {/* CONTINUOUS STEEL TRACK BETWEEN STATIONS */}
                {!isLast && (
                  <div className="relative ml-[70px] sm:ml-[76px] w-7 flex flex-col items-center">
                    {isActiveSegment ? (
                      /* ACTIVE RUNNING SEGMENT WITH LIVE GLIDING LOCOMOTIVE */
                      <div
                        ref={trainMarkerRef}
                        className="w-full relative min-h-[110px] flex flex-col items-center py-1"
                      >
                        {/* Cleared Green Track */}
                        <div
                          className="absolute top-0 w-1.5 bg-[#22C55E] rounded-full transition-all duration-75"
                          style={{ height: `${segProgress * 100}%` }}
                        />

                        {/* Upcoming Slate Track */}
                        <div
                          className="absolute bottom-0 w-1.5 bg-[#232A36] rounded-full"
                          style={{ height: `${(1 - segProgress) * 100}%` }}
                        />

                        {/* 🚆 THE GLIDING LOCOMOTIVE BADGE (60FPS rAF) */}
                        <div
                          className="absolute z-20 -translate-y-1/2 left-0 flex items-center gap-2 transition-transform duration-75"
                          style={{ top: `${segProgress * 100}%` }}
                        >
                          {/* Locomotive Head on Track */}
                          <div
                            className={`w-7 h-7 rounded-full bg-[#08090B] border-2 border-[#F59E0B] shadow-[0_0_16px_rgba(245,158,11,0.9)] flex items-center justify-center shrink-0 ${
                              motion.mode === 'moving'
                                ? 'ring-4 ring-[#F59E0B]/40 motion-safe:animate-pulse'
                                : ''
                            }`}
                          >
                            <span className="text-xs">🚆</span>
                          </div>

                          {/* Horizontal Telemetry Callout Pill */}
                          <div className="flex items-center gap-1.5 sm:gap-2 px-2 py-0.5 rounded bg-[#12151B] border border-[#F59E0B] shadow-xl font-mono text-[11px] sm:text-xs whitespace-nowrap">
                            <span className="text-[#22C55E] font-bold tabular-nums">
                              {Math.round(motion.displaySpeed)} km/h
                            </span>
                            <span className="text-[#64748B]">·</span>
                            <span className="text-[#F8FAFC] font-semibold">
                              {nextStn ? `${Math.max(0, Math.round(nextStn.distance_km - currentDrKm))} km to ${nextStn.station_code}` : ''}
                            </span>
                            <ArrowDown className="w-3 h-3 text-[#F59E0B] animate-bounce" />
                          </div>
                        </div>

                        {/* Wayside Waypoints */}
                        {segmentWaypoints.map((wp: any) => {
                          const isWpPassed = currentDrKm >= wp.km;
                          return (
                            <div
                              key={wp.code}
                              className="absolute left-9 z-10 flex items-center gap-1 text-[10px] font-mono whitespace-nowrap text-[#64748B]"
                              style={{
                                top: `${((wp.km - stn.distance_km) / (nextStn.distance_km - stn.distance_km)) * 100}%`,
                              }}
                            >
                              <span className={`w-1 h-1 rounded-full ${isWpPassed ? 'bg-[#22C55E]' : 'bg-[#475569]'}`} />
                              <span>{wp.name} ({wp.km} km) {isWpPassed && '✓'}</span>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      /* STATIC CONTINUOUS RAIL TRACK */
                      <div className="w-full h-7 flex items-center justify-center relative">
                        <div
                          className={`w-1.5 h-full rounded-full ${
                            isPassed ? 'bg-[#22C55E]' : 'bg-[#232A36]'
                          }`}
                        />
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* ========================================================================= */}
        {/* 3. COLLAPSIBLE BOTTOM DRAWER: WHY LATE AUTOPSY & PROVENANCE               */}
        {/* ========================================================================= */}
        <div className="mt-5 space-y-3 pt-3 border-t border-[#1E232E]">
          {/* Autopsy Card ("Why Is My Train Late?") */}
          <div className="bg-[#12151B] border border-[#232A36] rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-[#F8FAFC]">
                  {lang === 'HI' ? 'देरी का कारण (ऑटोप्सी)' : 'Why Is My Train Late?'}
                </span>
                <span className="px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-[#22C55E]/10 border border-[#22C55E]/30 text-[#22C55E]">
                  VERIFIED
                </span>
              </div>

              <button
                type="button"
                onClick={() => setWhyExpanded(!whyExpanded)}
                className="text-xs font-mono text-[#F59E0B] hover:underline flex items-center gap-1"
              >
                <span>{whyExpanded ? 'Collapse' : 'Details'}</span>
                {whyExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>
            </div>

            <p className="text-xs text-[#94A3B8] leading-relaxed">
              {lang === 'HI' ? autopsy.headline_hi : autopsy.headline}
            </p>

            {whyExpanded && (
              <div className="pt-2 space-y-2 border-t border-[#1E232E]">
                {autopsy.causes.map((c: any, i: number) => (
                  <div
                    key={i}
                    className="p-2 bg-[#0E1117] border border-[#1E232E] rounded text-xs font-mono flex items-start justify-between gap-2"
                  >
                    <div>
                      <div className="text-[#F8FAFC]">{lang === 'HI' ? c.plain_text_hi : c.plain_text}</div>
                      <div className="text-[10px] text-[#64748B]">{c.evidence_ref}</div>
                    </div>
                    <div className="font-bold text-[#F59E0B]">+{c.minutes}m</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer Provenance */}
          <footer className="py-3 text-center text-xs font-mono text-[#64748B] space-y-1.5">
            <div>
              {motion.isInterpolating
                ? `Position: Dead-reckoned from fix ${motion.lastFixAgeSeconds}s ago`
                : `Position: Live telemetry fix ${motion.lastFixAgeSeconds}s ago`}
              {' · '}auto 5s{' · '}{provenance.clock_mode} mode
            </div>
            <div className="flex items-center justify-center gap-3 pt-1">
              <button
                type="button"
                onClick={handleCopyShare}
                className="text-xs text-[#94A3B8] hover:text-[#F8FAFC] flex items-center gap-1 min-h-[32px]"
              >
                <Share2 className="w-3 h-3" />
                <span>{copiedLink ? 'Copied Link ✓' : 'Share Train'}</span>
              </button>
              <span>·</span>
              <button
                type="button"
                onClick={(e) => openModal(undefined, e.currentTarget)}
                className="text-xs text-[#F59E0B] hover:underline flex items-center gap-1 min-h-[32px]"
              >
                <Search className="w-3 h-3" />
                <span>Track another train</span>
              </button>
            </div>
          </footer>
        </div>
      </main>

      {/* ========================================================================= */}
      {/* 4. FLOATING "LOCATE TRAIN" FAB (WHERE IS MY TRAIN SIGNATURE BUTTON)       */}
      {/* ========================================================================= */}
      <div className="fixed bottom-6 right-4 sm:right-8 z-30 flex flex-col items-end gap-2">
        <button
          type="button"
          onClick={scrollToTrain}
          className="px-3 py-2 rounded-full bg-[#12151B] hover:bg-[#1E232E] border-2 border-[#F59E0B] text-[#F59E0B] shadow-[0_4px_20px_rgba(245,158,11,0.4)] flex items-center gap-1.5 text-xs font-mono font-bold transition-all active:scale-95"
          title="Center on Live Train"
        >
          <LocateFixed className="w-4 h-4" />
          <span>Locate Train</span>
        </button>
      </div>
    </div>
  );
}
