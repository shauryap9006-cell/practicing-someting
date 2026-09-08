import React from 'react';
import type { StationBoardPayload, CorridorStation } from '@railtwin/shared-types';
import { getDelayStatusBadge } from '../lib/motion';

interface StationBoardProps {
  board: StationBoardPayload | null;
  stations: CorridorStation[];
  currentStationIdx: number;
  onSelectStationIdx: (idx: number) => void;
  autoCycle: boolean;
  onToggleAutoCycle: () => void;
  cycleSecondsLeft: number;
}

export const StationBoard: React.FC<StationBoardProps> = ({
  board,
  stations,
  currentStationIdx,
  onSelectStationIdx,
  autoCycle,
  onToggleAutoCycle,
  cycleSecondsLeft,
}) => {
  const currentStation = stations[currentStationIdx] || {
    code: 'NDLS',
    name: 'New Delhi',
    name_hi: 'नई दिल्ली',
    platforms: 16,
  };

  const entries = board?.entries?.slice(0, 6) || [];

  return (
    <div className="station-board-panel">
      {/* Panel Header: Bilingual Station Identity & Cycle Status */}
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: 'var(--kiosk-gold)' }}>● PIDS</span>
          <span style={{ color: 'var(--text-dim)' }}>&bull;</span>
          <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
            {currentStation.name.toUpperCase()} ({currentStation.code})
          </span>
          <span style={{ color: 'var(--ochre)', fontFamily: 'var(--font-hindi)', fontSize: '11px', fontWeight: 600 }}>
            {currentStation.name_hi || ''}
          </span>
          <span style={{ color: 'var(--text-dim)', fontSize: '9.5px' }}>
            [{currentStation.platforms || 8} PF]
          </span>
        </div>

        {/* Auto Cycle Control & Countdown */}
        <div
          className={`cycle-control ${autoCycle ? 'running' : ''}`}
          onClick={onToggleAutoCycle}
          title={autoCycle ? 'Click to Pause Auto-Cycle' : 'Click to Resume Auto-Cycle'}
        >
          <span>{autoCycle ? 'AUTO' : 'PAUSED'}</span>
          <span style={{ color: autoCycle ? 'var(--kiosk-gold)' : 'var(--text-dim)', fontWeight: 700 }}>
            ({cycleSecondsLeft}s)
          </span>
          <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
            {autoCycle ? '[II]' : '[>]'}
          </span>
        </div>
      </div>

      {/* Interactive Station Switcher Pills */}
      <div className="station-selector-bar">
        {stations.map((stn, idx) => {
          const isActive = idx === currentStationIdx;
          return (
            <button
              key={stn.code}
              className={`station-pill-btn ${isActive ? 'active' : ''}`}
              onClick={() => onSelectStationIdx(idx)}
              title={`Switch to ${stn.name} (${stn.code})`}
            >
              {stn.code}
            </button>
          );
        })}
      </div>

      {/* PIDS Board Table */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <table className="board-table">
          <thead>
            <tr>
              <th style={{ width: '14%' }}>गाड़ी / TRAIN</th>
              <th style={{ width: '30%' }}>गाड़ी का नाम / NAME</th>
              <th style={{ width: '12%' }}>समय / SCHED</th>
              <th style={{ width: '12%' }}>अपेक्षित / EXP</th>
              <th style={{ width: '12%' }}>विलंब / DELAY</th>
              <th style={{ width: '8%' }}>PF</th>
              <th style={{ width: '12%' }}>स्थिति / STATUS</th>
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '28px 0', color: 'var(--text-dim)', fontSize: '10.5px' }}>
                  AWAITING LIVE PIDS TIMETABLE FOR {currentStation.code}…
                </td>
              </tr>
            ) : (
              entries.map((entry, idx) => {
                const badge = getDelayStatusBadge(entry.delay_min);
                const schedTime = entry.sched_dep || entry.sched_arr || '--:--';
                const expTime = entry.exp_dep || entry.exp_arr || schedTime;
                const cqr = entry.cqr_interval ? `±${Math.round(Math.abs(entry.cqr_interval[1] - entry.cqr_interval[0]) / 2)}m` : '';

                return (
                  <tr key={`${entry.train_no}-${idx}`}>
                    <td>
                      <span style={{ fontWeight: 700, color: 'var(--kiosk-gold)' }}>
                        #{entry.train_no}
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          color: 'var(--text-primary)',
                          display: 'inline-block',
                          maxWidth: '180px',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          verticalAlign: 'bottom',
                          fontFamily: 'var(--font-sans)',
                          fontWeight: 500,
                        }}
                        title={entry.train_name}
                      >
                        {entry.train_name.replace(/(Express|Special|Superfast|Passenger|MEMU|Rajdhani|Shatabdi)/gi, '').trim() || entry.train_name}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-dim)' }}>{schedTime}</td>
                    <td style={{ color: badge.color, fontWeight: 600 }}>{expTime}</td>
                    <td>
                      <span
                        style={{
                          color: badge.color,
                          backgroundColor: badge.bg,
                          border: `1px solid ${badge.border}`,
                          padding: '1px 5px',
                          borderRadius: '2px',
                          fontSize: '9.5px',
                          fontWeight: 700,
                        }}
                      >
                        {badge.label} {cqr && <span style={{ opacity: 0.8, fontSize: '8px' }}>{cqr}</span>}
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          color: 'var(--ochre)',
                          background: 'var(--ochre-wash)',
                          border: '1px solid var(--line-ochre)',
                          padding: '1px 5px',
                          borderRadius: '2px',
                          fontWeight: 700,
                          fontSize: '9.5px',
                        }}
                      >
                        {entry.platform ? `P${entry.platform}` : '--'}
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          fontSize: '9.5px',
                          fontWeight: 600,
                          color: entry.has_setout
                            ? 'var(--text-dim)'
                            : entry.has_setin
                            ? 'var(--kiosk-gold)'
                            : badge.color,
                        }}
                      >
                        {entry.status}
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
