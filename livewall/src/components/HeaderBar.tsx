import React from 'react';
import type { ClockData, NetworkState, ConnectionStatus, LivePosition, StationMeta } from '../lib/types';
import { getDelayColor } from '../lib/motion';
import { SearchBar } from './SearchBar';

interface HeaderBarProps {
  clock: ClockData | null;
  network: NetworkState | null;
  connection: ConnectionStatus;
  isStale: boolean;
  corridorName?: string;
  positions: LivePosition[];
  stations: StationMeta[];
  onSelectTrain: (trainNo: string) => void;
  onSelectStation: (stationCode: string) => void;
  onSelectCorridor: (corridorId: string) => void;
}

export const HeaderBar: React.FC<HeaderBarProps> = ({
  clock,
  network,
  connection,
  isStale,
  corridorName,
  positions,
  stations,
  onSelectTrain,
  onSelectStation,
  onSelectCorridor,
}) => {
  // Format virtual clock time
  let timeStr = '--:--:--';
  let dateStr = '07 SEP 2026';
  if (clock?.sim_now) {
    try {
      const d = new Date(clock.sim_now);
      timeStr = d.toTimeString().split(' ')[0] || '--:--:--';
      dateStr = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase();
    } catch {
      timeStr = clock.sim_now.slice(11, 19);
    }
  }

  const accel = clock?.accel ?? 1.0;
  const activeTrains = positions.length || network?.active_trains_count || 0;
  const delayedTrains = positions.filter(p => (p.delay_minutes || 0) > 15).length || network?.delayed_trains_count || 0;
  const onTimeTrains = Math.max(0, activeTrains - delayedTrains);
  const otpPct = activeTrains > 0 ? Math.round((onTimeTrains / activeTrains) * 100) : 100;
  const activeConflicts = network?.active_conflicts_count ?? 0;

  // Calculate average delay
  let avgDelay = 0;
  if (positions.length > 0) {
    const total = positions.reduce((acc, t) => acc + (t.delay_minutes || 0), 0);
    avgDelay = Math.round(total / positions.length);
  } else if (network?.trains && network.trains.length > 0) {
    const total = network.trains.reduce((acc, t) => acc + (t.current_delay_min || 0), 0);
    avgDelay = Math.round(total / network.trains.length);
  }

  const avgDelayColor = getDelayColor(avgDelay);
  const statusType = connection === 'offline' ? 'offline' : isStale ? 'stale' : 'live';

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  };

  return (
    <header className="header-bar">
      {/* Left: Operations Control Branding */}
      <div className="header-left">
        <div className="header-insignia" title="Indian Railways Station Master / RailTwin-X">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="#C25E00" strokeWidth="2" />
            <circle cx="12" cy="12" r="4" fill="#C25E00" />
            <line x1="12" y1="2" x2="12" y2="22" stroke="#C25E00" strokeWidth="1.5" strokeDasharray="2 2" />
            <line x1="2" y1="12" x2="22" y2="12" stroke="#C25E00" strokeWidth="1.5" strokeDasharray="2 2" />
          </svg>
        </div>
        <div className="header-title-box">
          <div className="header-brand">
            RAILTWIN-X <span className="header-brand-badge">STATION MASTER OCC</span>
          </div>
          <div className="header-subtext">
            INDIAN RAILWAYS &bull; ALL-INDIA DIGITAL TWIN DISPATCH CONTROLLER
          </div>
        </div>

        {/* Virtual Clock Telemetry */}
        <div className="clock-telemetry" style={{ marginLeft: '12px', paddingLeft: '12px', borderLeft: '1px solid var(--line-subtle)' }}>
          <span className="clock-date">{dateStr}</span>
          <span className="clock-display">{timeStr}</span>
          <span className="accel-badge" style={{ marginLeft: '6px' }}>
            x{accel.toFixed(1)} {accel > 1 ? 'SIM' : 'REAL'}
          </span>
        </div>
      </div>

      {/* Center: Universal Instant Search Bar */}
      <div className="header-center" style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
        <SearchBar
          positions={positions}
          network={network}
          stations={stations}
          onSelectTrain={onSelectTrain}
          onSelectStation={onSelectStation}
          onSelectCorridor={onSelectCorridor}
        />
      </div>

      {/* Right: Active Corridor Badge + Telemetry Counts + Fullscreen + Connection Status */}
      <div className="header-right">
        <div className="stat-pill" title="Active Indian Railways Corridor" style={{ borderColor: 'var(--ochre)' }}>
          <span className="stat-label">CORRIDOR</span>
          <span className="stat-val" style={{ color: 'var(--kiosk-gold)', fontSize: '10.5px' }}>
            {corridorName || 'Northern Mainline'}
          </span>
        </div>

        <div className="stat-pill">
          <span className="stat-label">Fleet</span>
          <span className="stat-val" style={{ color: 'var(--text-primary)' }}>
            {activeTrains}
          </span>
        </div>

        <div className="stat-pill">
          <span className="stat-label">OTP</span>
          <span className="stat-val" style={{ color: 'var(--signal-green)' }}>
            {otpPct}%
          </span>
        </div>

        <div className="stat-pill">
          <span className="stat-label">Avg Delay</span>
          <span className="stat-val" style={{ color: avgDelayColor }}>
            {avgDelay > 0 ? `+${avgDelay}m` : '0m'}
          </span>
        </div>

        {/* Fullscreen Button */}
        <button
          className="fullscreen-btn"
          onClick={toggleFullscreen}
          title="Toggle Fullscreen"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
          </svg>
          <span>FULLSCREEN</span>
        </button>

        {/* Connection status pill */}
        <div className={`connection-pill ${statusType}`}>
          <div className={`status-dot ${statusType}`} />
          <span>{statusType.toUpperCase()}</span>
        </div>
      </div>
    </header>
  );
};
export default HeaderBar;
