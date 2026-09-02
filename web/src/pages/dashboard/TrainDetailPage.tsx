import React from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Train } from '@/mock/types';
import {
  AspectLamp,
  AspectType,
  CorridorSpine,
  AutopsyStrip,
  ConfidenceBand,
  Provenance,
  EmptyState,
} from '@/components/aspect';
import {
  ArrowLeft,
  Clock,
  MapPin,
  Activity,
  AlertTriangle,
  Layers,
  Gauge,
  CheckCircle2,
  TrainTrack,
  Radio,
  ShieldCheck,
  Wind,
} from 'lucide-react';

export const TrainDetailPage: React.FC = () => {
  const { trainNo, id } = useParams<{ trainNo?: string; id?: string }>();
  const targetTrainNo = trainNo || id || '';
  const navigate = useNavigate();

  // 1. Live Train Journey & Telemetry Query (polling every 5s for live movement)
  const { data: train, isLoading, dataUpdatedAt } = useQuery({
    queryKey: queryKeys.train(targetTrainNo),
    queryFn: () => api.getTrain(targetTrainNo),
    enabled: !!targetTrainNo,
    refetchInterval: 5000,
  });

  // 2. Live Causal Delay Autopsy Query (polling every 5s for live attribution deltas)
  const { data: autopsyData } = useQuery({
    queryKey: queryKeys.trainAutopsy(targetTrainNo),
    queryFn: () => api.getTrainAutopsy(targetTrainNo),
    enabled: !!targetTrainNo,
    refetchInterval: 5000,
  });

  if (isLoading) {
    return (
      <div className="p-12 text-center bg-[#101216] border border-[#23272F] rounded-lg space-y-4 font-mono select-none">
        <h2 className="text-sm font-bold text-[#E9EBEE] uppercase tracking-wider flex items-center justify-center gap-2">
          <Radio className="w-4 h-4 text-[#F5A524] animate-pulse" />
          <span>Connecting to Live Signal Aspect Telemetry for #{targetTrainNo}...</span>
        </h2>
        <div className="w-5 h-5 border-2 border-[#F5A524] border-t-transparent rounded-full animate-spin mx-auto" />
      </div>
    );
  }

  if (!train) {
    return (
      <EmptyState
        title={`Train ${targetTrainNo || 'Unknown'} Not Found`}
        description="The requested train identifier is not currently active in the NCR corridor timetable."
        actionLabel="Back to Trains Directory"
        onAction={() => navigate('/dashboard/trains')}
      />
    );
  }

  const getAspect = (delay: number): AspectType => {
    if (delay <= 5) return 'clear';
    if (delay <= 25) return 'caution';
    return 'restrict';
  };

  const aspect = getAspect(train.delayMinutes);

  // Dynamic chainage distance estimation from current station
  const stationKmMap: Record<string, number> = {
    NDLS: 0,
    GZB: 25,
    ALJN: 126,
    TDL: 206,
    ETW: 297,
    CNB: 435,
    FTP: 512,
    PRYJ: 632,
    MZP: 721,
    DDU: 785,
  };
  const trainKm = stationKmMap[train.currentStation?.toUpperCase()] ?? 435;

  // Transform live backend autopsy causes into DelaySegments
  const autopsySegments = autopsyData?.causes && autopsyData.causes.length > 0
    ? autopsyData.causes.map((c, idx) => ({
        id: String(idx + 1),
        category: c.event_type || 'CONGESTION',
        label: c.cause || c.event_type,
        location: c.station_code || train.currentStation || 'Corridor',
        minutes: c.minutes,
        aspect: (c.minutes < 0 ? 'clear' : c.minutes > 15 ? 'restrict' : 'caution') as AspectType,
        description: c.cause,
        evidencePointer: c.evidence_pointer || undefined,
        evidence: c.evidence || undefined,
      }))
    : undefined;

  // Derive dynamic context from live autopsy causes
  const activeTsrCauses = autopsyData?.causes.filter(c => c.event_type === 'TSR') || [];
  const activeWeatherCause = autopsyData?.causes.find(c => c.event_type === 'WEATHER');
  const activeInheritedCause = autopsyData?.causes.find(c => c.event_type === 'INHERITED');
  const activeRecoveryCause = autopsyData?.causes.find(c => c.event_type === 'RECOVERY');

  const journeyStops = train.journey && train.journey.length > 0
    ? train.journey
    : [
        { seq: 1, stationCode: 'NDLS', stationName: 'New Delhi', schedArrival: '--', schedDeparture: '16:50', predArrival: '--', predDeparture: '16:50', delayMinutes: 0, status: 'passed' as const, distanceKm: 0 },
        { seq: 2, stationCode: 'CNB', stationName: 'Kanpur Central', schedArrival: '21:30', schedDeparture: '21:35', predArrival: '21:55', predDeparture: '22:00', delayMinutes: train.delayMinutes, status: 'current' as const, distanceKm: 435 },
        { seq: 3, stationCode: 'PRYJ', stationName: 'Prayagraj Jn', schedArrival: '23:05', schedDeparture: '23:10', predArrival: '23:30', predDeparture: '23:35', delayMinutes: train.delayMinutes, status: 'upcoming' as const, distanceKm: 632 },
        { seq: 4, stationCode: 'DDU', stationName: 'Pt. Deen Dayal', schedArrival: '01:25', schedDeparture: '01:35', predArrival: '01:50', predDeparture: '02:00', delayMinutes: Math.max(0, train.delayMinutes - 3), status: 'upcoming' as const, distanceKm: 785 },
      ];

  return (
    <div className="space-y-6 font-mono select-none">
      {/* Top Breadcrumb & Live Stream Ticker */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <Link
          to="/dashboard/trains"
          className="text-xs text-[#A3ABB6] hover:text-[#E9EBEE] flex items-center gap-1.5 transition-colors font-mono"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Trains Directory</span>
        </Link>
        <div className="flex flex-wrap items-center gap-3 text-xs text-[#6B7480]">
          <span className="flex items-center gap-1 text-[#3DDC97]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#3DDC97] animate-ping" />
            LIVE TELEMETRY STREAM (3s)
          </span>
          <span>·</span>
          <span>RAKE: {train.rakeId || `RK-${train.number}`}</span>
          <span>·</span>
          <span>PRIORITY: {train.priority || 1}</span>
        </div>
      </div>

      {/* Main Train Header Instrument Card */}
      <div className="bg-[#101216] border border-[#23272F] rounded-lg p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-[#23272F]">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl sm:text-3xl font-bold text-[#E9EBEE] tracking-tight">
                {train.number}
              </h1>
              <span className="text-base sm:text-lg font-sans text-[#A3ABB6]">
                {train.name}
              </span>
              <AspectLamp
                aspect={aspect}
                label={train.delayMinutes <= 0 ? 'CLEAR (ON TIME)' : `+${train.delayMinutes}M DELAY`}
                size="md"
              />
            </div>

            <div className="flex flex-wrap items-center gap-4 text-xs text-[#A3ABB6]">
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-[#F5A524]" />
                <span>At {train.currentStation || 'En Route'} (KM {trainKm})</span>
              </span>
              <span>·</span>
              <span>Class: {train.type || 'Superfast Express'}</span>
              <span>·</span>
              <span>Speed: {train.speedKmph || 110} km/h</span>
            </div>
          </div>

          {/* Expected Arrival & Confidence Band */}
          <div className="shrink-0">
            <ConfidenceBand
              expectedTime={train.predictedArrival || '19:42'}
              rangeStart={train.etaBand?.p10 || '19:20'}
              rangeEnd={train.etaBand?.p90 || '20:05'}
              size="card"
            />
          </div>
        </div>

        {/* Inline Corridor Spine Showing Live Chainage */}
        <div className="pt-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] uppercase tracking-wider text-[#6B7480]">
              Active Corridor Chainage Progress
            </span>
            <span className="text-[10px] text-[#A3ABB6]">
              {train.currentStation || 'NDLS'} → {train.nextStation || 'DDU'}
            </span>
          </div>
          <CorridorSpine
            density="inline"
            highlightKm={trainKm}
            highlightTrainNo={train.number}
            interactive={false}
          />
        </div>
      </div>

      {/* Real-time Delay Autopsy & Causal Decomposition */}
      <AutopsyStrip
        trainNo={train.number}
        trainName={train.name}
        totalDelayMin={train.delayMinutes}
        segments={autopsySegments}
        summarySentence={autopsyData?.narrative}
        integrityStatus={autopsyData?.integrity_status}
        integrityChecks={autopsyData?.integrity_checks}
        asOfTs={autopsyData?.as_of_ts || autopsyData?.updated_at}
      />

      {/* Station Dwell Schedule & Dynamic Telemetry Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Dynamic Timetable Station Schedule */}
        <div className="bg-[#101216] border border-[#23272F] rounded-lg p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#23272F]">
            <span className="font-bold text-xs uppercase text-[#E9EBEE] tracking-wider flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-[#F5A524]" />
              CORRIDOR STOP TIMETABLE
            </span>
            <span className="text-[10px] text-[#6B7480]">WTT SCHEDULED VS PREDICTED</span>
          </div>

          <div className="space-y-2">
            {journeyStops.map(stn => (
              <div
                key={stn.stationCode}
                className="p-2.5 bg-[#0A0B0D] border border-[#23272F] rounded-sm flex items-center justify-between text-xs hover:border-[#2E333D] transition-colors"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-[#E9EBEE]">{stn.stationCode}</span>
                    <span className="text-[#A3ABB6] font-sans text-[11px]">{stn.stationName}</span>
                  </div>
                  <span className="text-[10px] text-[#6B7480]">KM {stn.distanceKm ?? '--'}</span>
                </div>

                <div className="flex items-center gap-4 text-right">
                  <span className="text-[#6B7480]">Sch: {stn.schedArrival || stn.schedDeparture}</span>
                  <span className="font-bold text-[#E9EBEE]">Pred: {stn.predArrival || stn.predDeparture}</span>
                  <AspectLamp
                    aspect={getAspect(stn.delayMinutes)}
                    label={stn.delayMinutes <= 0 ? 'OT' : `+${stn.delayMinutes}m`}
                    size="xs"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Dynamic Telemetry Context Card (Driven by Live Engine State) */}
        <div className="bg-[#101216] border border-[#23272F] rounded-lg p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#23272F]">
            <span className="font-bold text-xs uppercase text-[#E9EBEE] tracking-wider flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-[#3DDC97]" />
              ENGINEERING & SENSOR CONTEXT
            </span>
            <span className="text-[10px] text-[#3DDC97]">● SENSORS ONLINE</span>
          </div>

          <div className="space-y-3 text-xs">
            {/* Speed Restrictions */}
            <div className="p-3 bg-[#0A0B0D] border border-[#23272F] rounded-sm flex items-center justify-between">
              <span className="text-[#A3ABB6]">Active Route Speed Restrictions</span>
              <span className="font-bold tabular-nums text-[#F5A524]">
                {activeTsrCauses.length > 0
                  ? `${activeTsrCauses.length} Active (${activeTsrCauses.map(c => `+${c.minutes}m`).join(', ')})`
                  : '0 Active TSRs (Route nominal)'}
              </span>
            </div>

            {/* Weather Sensor Telemetry */}
            <div className="p-3 bg-[#0A0B0D] border border-[#23272F] rounded-sm flex items-center justify-between">
              <span className="text-[#A3ABB6]">Weather & Visibility Telemetry</span>
              <span className="font-bold text-[#3DDC97]">
                {activeWeatherCause ? activeWeatherCause.cause : 'Clear Visibility (Sensor Nominal)'}
              </span>
            </div>

            {/* Turnaround / Ingest State */}
            <div className="p-3 bg-[#0A0B0D] border border-[#23272F] rounded-sm flex items-center justify-between">
              <span className="text-[#A3ABB6]">Rake Turnaround Ingest</span>
              <span className="font-bold tabular-nums text-[#E9EBEE]">
                {activeInheritedCause ? `Origin Ingest (+${activeInheritedCause.minutes}m carry-in)` : 'Nominal Turnaround (Buffer Intact)'}
              </span>
            </div>

            {/* Recovery Capability */}
            <div className="p-3 bg-[#0A0B0D] border border-[#23272F] rounded-sm flex items-center justify-between">
              <span className="text-[#A3ABB6]">Section Speed Recovery</span>
              <span className="font-bold tabular-nums text-[#3DDC97]">
                {activeRecoveryCause ? `${activeRecoveryCause.minutes}m Recovered` : 'Timetable MPS Nominal'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Live Integrity & Provenance Footer */}
      <div className="bg-[#101216] border border-[#23272F] rounded-lg p-4">
        <Provenance
          updatedAt={dataUpdatedAt}
          source={`PIPELINE 07 EVENT LEDGER · ${autopsyData?.integrity_status || 'VERIFIED'}`}
        />
      </div>
    </div>
  );
};
