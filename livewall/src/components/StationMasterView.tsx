import React, { useMemo } from 'react';
import type {
  StationMeta,
  StationBoardPayload,
  LivePosition,
  PlatformState,
  NetworkState,
  CorridorStation,
} from '@railtwin/shared-types';
import { getDelayStatusBadge } from '../lib/motion';

interface StationMasterViewProps {
  station: StationMeta;
  corridorStations?: CorridorStation[];
  allStations: StationMeta[];
  board: StationBoardPayload | null;
  positions: LivePosition[];
  platformStates: PlatformState[];
  network: NetworkState | null;
  onSelectStation: (stationCode: string) => void;
  onSelectTrain: (trainNo: string) => void;
}

export const StationMasterView: React.FC<StationMasterViewProps> = ({
  station,
  corridorStations,
  allStations,
  board,
  positions,
  platformStates,
  network,
  onSelectStation,
  onSelectTrain,
}) => {
  // Network train lookup map
  const trainDetailMap = useMemo(() => {
    const map = new Map<string, { name: string; class: string; delay: number }>();
    if (network?.trains) {
      for (const t of network.trains) {
        map.set(t.train_no, {
          name: t.train_name,
          class: t.train_class,
          delay: t.current_delay_min,
        });
      }
    }
    return map;
  }, [network]);

  const stnCode = station.code.toUpperCase();
  const platformCount = station.platforms || 8;

  // 1. Berthed trains at this station ("Which train is there")
  const berthedTrains = useMemo(() => {
    const list: Array<{
      platform: number;
      trainNo: string;
      trainName: string;
      direction: string;
      schedDep: string | null;
      expDep: string | null;
      delayMin: number;
      starterAspect: 'GREEN' | 'RED';
      statusText: string;
      source: string;
    }> = [];

    // From board entries
    if (board?.entries) {
      for (const e of board.entries) {
        if (e.has_setin && !e.has_setout) {
          const pfNum = typeof e.platform === 'number' ? e.platform : parseInt(String(e.platform), 10) || 1;
          list.push({
            platform: pfNum,
            trainNo: e.train_no,
            trainName: e.train_name,
            direction: e.direction || 'UP',
            schedDep: e.sched_dep,
            expDep: e.exp_dep,
            delayMin: e.delay_min || 0,
            starterAspect: e.delay_min > 20 ? 'RED' : 'GREEN',
            statusText: e.delay_min > 20 ? 'HALTED' : 'BOARDING',
            source: 'board',
          });
        }
      }
    }

    // From live positions currently at this station
    const liveAtStation = positions.filter(
      (p) => p.current_station_code?.toUpperCase() === stnCode && !list.some((item) => item.trainNo === p.train_no)
    );

    for (let i = 0; i < liveAtStation.length; i++) {
      const p = liveAtStation[i];
      const detail = trainDetailMap.get(p.train_no);
      const assignedPf = ((i % platformCount) + 1);
      const isHold = p.signal_hold_active;
      list.push({
        platform: assignedPf,
        trainNo: p.train_no,
        trainName: detail?.name || 'Corridor Express',
        direction: parseInt(p.train_no, 10) % 2 !== 0 ? 'UP' : 'DN',
        schedDep: null,
        expDep: 'DWELLING',
        delayMin: p.delay_minutes || 0,
        starterAspect: isHold ? 'RED' : 'GREEN',
        statusText: isHold ? 'SIGNAL HOLD' : 'DEP DWELLING',
        source: 'telemetry',
      });
    }

    return list;
  }, [board, positions, stnCode, platformCount, trainDetailMap]);

  // 2. Approaching Inbound Trains ("Which train is coming")
  const approachingTrains = useMemo(() => {
    return positions
      .filter((p) => p.next_station_code?.toUpperCase() === stnCode)
      .map((p, idx) => {
        const detail = trainDetailMap.get(p.train_no);
        const assignedPf = ((idx % platformCount) + 1);
        const estMinutes = Math.max(2, Math.round(((100 - (p.progress_pct || 50)) / 100) * 22));
        const estDistanceKm = Math.max(1.2, ((100 - (p.progress_pct || 50)) / 100) * 35).toFixed(1);
        return {
          trainNo: p.train_no,
          trainName: detail?.name || 'Express Service',
          speedKmh: Math.round(p.speed_kmh),
          delayMin: p.delay_minutes || 0,
          assignedPf,
          homeAspect: p.signal_hold_active ? 'RED' : (p.delay_minutes > 15 ? 'YELLOW' : 'GREEN'),
          etaMinutes: estMinutes,
          distanceKm: estDistanceKm,
          section: p.section_id ? p.section_id.replace('_', ' -> ') : 'Approach Block',
        };
      })
      .sort((a, b) => a.etaMinutes - b.etaMinutes);
  }, [positions, stnCode, platformCount, trainDetailMap]);

  // Platform states map
  const platformStateMap = useMemo(() => {
    const map = new Map<number, PlatformState>();
    for (const ps of platformStates) {
      map.set(ps.platform, ps);
    }
    return map;
  }, [platformStates]);

  // Occupancy metrics
  const occupiedCount = berthedTrains.length;
  const yardCongestionPct = Math.min(100, Math.round((occupiedCount / platformCount) * 100));

  // Station jump list: prioritizes stations on the active corridor
  const stationPillList = useMemo(() => {
    if (corridorStations && corridorStations.length > 0) {
      return corridorStations;
    }
    return allStations.slice(0, 12);
  }, [corridorStations, allStations]);

  return (
    <div className="station-deck-container">
      {/* Station Control Header Bar */}
      <div className="station-deck-header">
        <div className="station-deck-identity">
          <div className="station-deck-title-group">
            <span className="station-deck-badge">[STATION MASTER]</span>
            <h2 className="station-deck-name">{station.name.toUpperCase()}</h2>
            <span className="station-deck-code">[{station.code}]</span>
            {station.name_hi && <span className="station-deck-hindi">{station.name_hi}</span>}
          </div>

          <div className="station-deck-metrics">
            <div className="deck-metric-box">
              <span className="deck-metric-lbl">PLATFORMS</span>
              <span className="deck-metric-num">{platformCount}</span>
            </div>
            <div className="deck-metric-box">
              <span className="deck-metric-lbl">BERTHED</span>
              <span className="deck-metric-num gold">{occupiedCount}</span>
            </div>
            <div className="deck-metric-box">
              <span className="deck-metric-lbl">APPROACHING</span>
              <span className="deck-metric-num green">{approachingTrains.length}</span>
            </div>
            <div className="deck-metric-box">
              <span className="deck-metric-lbl">YARD LOAD</span>
              <span
                className={`deck-metric-num ${
                  yardCongestionPct > 75 ? 'red' : yardCongestionPct > 45 ? 'amber' : 'green'
                }`}
              >
                {yardCongestionPct}%
              </span>
            </div>
          </div>
        </div>

        {/* Corridor Stations Switcher Pills */}
        <div className="station-deck-pills-row">
          <span className="station-deck-pills-label">CORRIDOR STATIONS:</span>
          <div className="station-deck-pills-scroll">
            {stationPillList.map((stn) => (
              <button
                key={stn.code}
                className={`station-deck-pill ${stn.code.toUpperCase() === stnCode ? 'active' : ''}`}
                onClick={() => onSelectStation(stn.code)}
                title={`${stn.name} (${stn.code})`}
              >
                <span className="pill-code">{stn.code}</span>
                <span className="pill-name">{stn.name.split(' ')[0]}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 3-Column Operations Deck: All details side-by-side with zero tabs */}
      <div className="station-deck-grid">
        {/* Column 1: WHICH TRAIN IS THERE (Platform Track Circuit Mimics) */}
        <div className="deck-column deck-column-platforms">
          <div className="deck-column-header">
            <div className="deck-column-title">
              <span className="deck-dot gold" />
              <span>PLATFORM BERTHS -- WHICH TRAIN IS THERE</span>
            </div>
            <span className="deck-column-tag">
              {occupiedCount} OF {platformCount} OCCUPIED
            </span>
          </div>

          <div className="deck-column-scrollable">
            <div className="platform-mimic-list">
              {Array.from({ length: platformCount }).map((_, idx) => {
                const pfNum = idx + 1;
                const berthed = berthedTrains.find((b) => b.platform === pfNum);
                const pfState = platformStateMap.get(pfNum);
                const isOccupied = Boolean(berthed) || pfState?.state === 'OCCUPIED';

                return (
                  <div
                    key={`pf-deck-${pfNum}`}
                    className={`platform-track-card ${isOccupied ? 'occupied' : 'vacant'}`}
                    onClick={() => {
                      if (berthed?.trainNo) onSelectTrain(berthed.trainNo);
                    }}
                  >
                    {/* Platform ID & Starter Signal Mast */}
                    <div className="platform-track-header">
                      <span className="platform-number-tag">P{pfNum}</span>
                      <div className="starter-signal-lamp">
                        <span className="starter-label">STARTER:</span>
                        <span
                          className={`starter-dot ${
                            isOccupied
                              ? berthed?.starterAspect === 'RED'
                                ? 'lamp-red'
                                : 'lamp-green'
                              : 'lamp-green'
                          }`}
                        />
                        <span className="starter-state">
                          {isOccupied ? berthed?.starterAspect || 'RED' : 'CLEAR'}
                        </span>
                      </div>
                    </div>

                    {/* Platform Content: Berthed Train Details OR Vacant Track Circuit */}
                    {isOccupied && berthed ? (
                      <div className="platform-occupied-body">
                        <div className="platform-train-row">
                          <span className="platform-train-no">#{berthed.trainNo}</span>
                          <span className="platform-train-name">{berthed.trainName}</span>
                          <span className="platform-dir-tag">{berthed.direction}</span>
                        </div>

                        <div className="platform-status-row">
                          <span className="platform-dwell-badge">{berthed.statusText}</span>
                          <span
                            className="platform-delay-badge"
                            style={{
                              color: berthed.delayMin <= 0 ? 'var(--signal-green)' : berthed.delayMin <= 15 ? 'var(--signal-amber)' : 'var(--signal-red)',
                            }}
                          >
                            {berthed.delayMin <= 0 ? 'ON TIME' : `+${berthed.delayMin}m`}
                          </span>
                          <span className="platform-dep-time">
                            DEP: {berthed.schedDep || berthed.expDep || 'CLEARANCE REQ'}
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div className="platform-vacant-body">
                        <div className="vacant-track-line" />
                        <span className="vacant-track-text">[TRACK CIRCUIT: CLEAR - VACANT]</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Column 2: WHICH TRAIN IS COMING (Inbound Approaching Queue) */}
        <div className="deck-column deck-column-inbound">
          <div className="deck-column-header">
            <div className="deck-column-title">
              <span className="deck-dot green" />
              <span>INBOUND QUEUE -- WHICH TRAIN IS COMING</span>
            </div>
            <span className="deck-column-tag">{approachingTrains.length} APPROACHING</span>
          </div>

          <div className="deck-column-scrollable">
            {approachingTrains.length === 0 ? (
              <div className="deck-empty-state">
                <span className="empty-icon">[CLEAR]</span>
                <span className="empty-title">NO INBOUND TRAINS IN APPROACH SECTION</span>
                <span className="empty-subtitle">Home signal normal, automatic block line clear.</span>
              </div>
            ) : (
              <div className="inbound-trains-list">
                {approachingTrains.map((app) => {
                  const delayBadge = getDelayStatusBadge(app.delayMin);

                  return (
                    <div
                      key={`inbound-${app.trainNo}`}
                      className="inbound-train-card"
                      onClick={() => onSelectTrain(app.trainNo)}
                    >
                      <div className="inbound-top-row">
                        <div className="inbound-train-id">
                          <span className="inbound-no">#{app.trainNo}</span>
                          <span className="inbound-name">{app.trainName}</span>
                        </div>
                        <span
                          className="inbound-delay-chip"
                          style={{
                            color: delayBadge.color,
                            backgroundColor: delayBadge.bg,
                            borderColor: delayBadge.border,
                          }}
                        >
                          {delayBadge.label}
                        </span>
                      </div>

                      <div className="inbound-stats-grid">
                        <div className="inbound-stat">
                          <span className="stat-label">ETA:</span>
                          <span className="stat-val eta">~{app.etaMinutes}m away</span>
                        </div>
                        <div className="inbound-stat">
                          <span className="stat-label">DISTANCE:</span>
                          <span className="stat-val">{app.distanceKm} km</span>
                        </div>
                        <div className="inbound-stat">
                          <span className="stat-label">SPEED:</span>
                          <span className="stat-val">{app.speedKmh} km/h</span>
                        </div>
                        <div className="inbound-stat">
                          <span className="stat-label">ASSIGNED PF:</span>
                          <span className="stat-val pf">P{app.assignedPf}</span>
                        </div>
                      </div>

                      <div className="inbound-signal-bar">
                        <div className="home-aspect-tag">
                          <span className="home-label">HOME SIGNAL:</span>
                          <span
                            className={`home-dot ${
                              app.homeAspect === 'RED'
                                ? 'lamp-red'
                                : app.homeAspect === 'YELLOW'
                                ? 'lamp-amber'
                                : 'lamp-green'
                            }`}
                          />
                          <span className="home-text">
                            {app.homeAspect === 'RED'
                              ? 'STOP (HOLD)'
                              : app.homeAspect === 'YELLOW'
                              ? 'APPROACH CAUTION'
                              : 'CLEAR (MAIN)'}
                          </span>
                        </div>
                        <span className="inbound-section-text">{app.section}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Column 3: STATION PIDS TIMETABLE & SIGNALS */}
        <div className="deck-column deck-column-timetable">
          <div className="deck-column-header">
            <div className="deck-column-title">
              <span className="deck-dot ochre" />
              <span>PIDS TIMETABLE -- ARRIVALS &amp; DEPARTURES</span>
            </div>
            <span className="deck-column-tag">
              {board?.entries ? `${board.entries.length} SCHEDULED` : 'LIVE PIDS'}
            </span>
          </div>

          <div className="deck-column-scrollable">
            {board?.entries && board.entries.length > 0 ? (
              <table className="station-deck-table">
                <thead>
                  <tr>
                    <th>TRAIN</th>
                    <th>NAME</th>
                    <th>SCHED</th>
                    <th>EXP</th>
                    <th>PF</th>
                    <th>DELAY</th>
                  </tr>
                </thead>
                <tbody>
                  {board.entries.slice(0, 14).map((e) => {
                    const delayMin = e.delay_min || 0;
                    const delayCol =
                      delayMin <= 0
                        ? 'var(--signal-green)'
                        : delayMin <= 15
                        ? 'var(--signal-amber)'
                        : 'var(--signal-red)';

                    return (
                      <tr
                        key={`pids-${e.train_no}`}
                        onClick={() => onSelectTrain(e.train_no)}
                        style={{ cursor: 'pointer' }}
                      >
                        <td className="pids-no">#{e.train_no}</td>
                        <td className="pids-name" title={e.train_name}>
                          {e.train_name}
                        </td>
                        <td className="pids-time">{e.sched_dep || e.sched_arr || '--:--'}</td>
                        <td className="pids-time exp">{e.exp_dep || e.exp_arr || '--:--'}</td>
                        <td className="pids-pf">P{e.platform || 1}</td>
                        <td className="pids-delay" style={{ color: delayCol }}>
                          {delayMin <= 0 ? 'ON TIME' : `+${delayMin}m`}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : (
              <div className="deck-empty-state">
                <span className="empty-icon">[PIDS]</span>
                <span className="empty-title">PIDS FEED SYNCHRONIZING</span>
                <span className="empty-subtitle">Gathering operational schedule from timetable store...</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default StationMasterView;
