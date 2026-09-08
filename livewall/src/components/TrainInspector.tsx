import React from 'react';
import type { LivePosition, NetworkState, StationMeta } from '@railtwin/shared-types';
import { getDelayColor } from '../lib/motion';

interface TrainInspectorProps {
  trainNo: string;
  positions: LivePosition[];
  network: NetworkState | null;
  stations: StationMeta[];
  onClose: () => void;
  onFocusTrain: (trainNo: string) => void;
  onSelectStation: (stationCode: string) => void;
}

export const TrainInspector: React.FC<TrainInspectorProps> = ({
  trainNo,
  positions,
  network,
  stations,
  onClose,
  onFocusTrain,
  onSelectStation,
}) => {
  const position = positions.find((p) => p.train_no === trainNo);
  const detail = network?.trains.find((t) => t.train_no === trainNo);

  if (!position && !detail) return null;

  const trainName = detail?.train_name || 'Scheduled Service';
  const trainClass = detail?.train_class ? detail.train_class.toUpperCase() : 'EXPRESS';
  const speed = Math.round(position?.speed_kmh || 0);
  const delay = position?.delay_minutes ?? detail?.current_delay_min ?? 0;
  const delayColor = getDelayColor(delay);
  const aspect = position?.inferred_signal_aspect || 'GREEN';

  const currentStn = position?.current_station_code || detail?.last_passed_station || '--';
  const nextStn = position?.next_station_code || detail?.next_station || '--';
  const dest = detail?.destination || 'TERMINAL';

  const aspectColor =
    aspect === 'GREEN'
      ? 'var(--signal-green)'
      : aspect === 'YELLOW'
      ? 'var(--signal-amber)'
      : 'var(--signal-red)';

  return (
    <div className="train-inspector-overlay">
      <div className="inspector-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: 'var(--kiosk-gold)', fontWeight: 800, fontSize: '13px' }}>
            #{trainNo}
          </span>
          <span
            style={{
              fontSize: '8.5px',
              padding: '1px 5px',
              borderRadius: '2px',
              background: 'var(--bg-night-0)',
              border: '1px solid var(--line-subtle)',
              color: 'var(--text-secondary)',
              fontWeight: 700,
            }}
          >
            {trainClass}
          </span>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-dim)',
            cursor: 'pointer',
            fontSize: '13px',
          }}
        >
          [X]
        </button>
      </div>

      <div className="inspector-body">
        <div style={{ fontSize: '11px', color: 'var(--text-primary)', fontWeight: 700 }}>
          {trainName}
        </div>

        <div className="inspector-grid">
          <div className="inspector-stat-box">
            <span style={{ fontSize: '8px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Speed / Kinematics
            </span>
            <div style={{ fontSize: '14px', fontWeight: 800, color: 'var(--text-primary)' }}>
              {speed} <span style={{ fontSize: '9px', fontWeight: 400 }}>km/h</span>
            </div>
          </div>

          <div className="inspector-stat-box">
            <span style={{ fontSize: '8px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Delay Status
            </span>
            <div style={{ fontSize: '14px', fontWeight: 800, color: delayColor }}>
              {delay > 0 ? `+${delay}m` : '0m ON-TIME'}
            </div>
          </div>

          <div className="inspector-stat-box">
            <span style={{ fontSize: '8px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Current Block / Station
            </span>
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--kiosk-gold)' }}>
              {currentStn}
            </div>
          </div>

          <div className="inspector-stat-box">
            <span style={{ fontSize: '8px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Next Scheduled Stop
            </span>
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--signal-green)' }}>
              {nextStn}
            </div>
          </div>
        </div>

        {/* Signal Aspect Pill */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--bg-night-0)',
            border: '1px solid var(--line-subtle)',
            borderRadius: '3px',
            padding: '6px 8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                backgroundColor: aspectColor,
                boxShadow: `0 0 8px ${aspectColor}`,
                display: 'inline-block',
              }}
            />
            <span style={{ fontSize: '10px', fontWeight: 700, color: aspectColor }}>
              ASPECT: {aspect}
            </span>
          </div>
          <span style={{ fontSize: '9px', color: 'var(--text-dim)' }}>
            DEST: {dest}
          </span>
        </div>

        {/* Action Buttons */}
        <div className="inspector-btn-row">
          <button className="inspector-action-btn" onClick={() => onFocusTrain(trainNo)}>
            [FOCUS MAP]
          </button>
          {nextStn !== '--' && (
            <button className="inspector-action-btn" onClick={() => onSelectStation(nextStn)}>
              [STN {nextStn}]
            </button>
          )}
          {currentStn !== '--' && currentStn !== nextStn && (
            <button className="inspector-action-btn" onClick={() => onSelectStation(currentStn)}>
              [STN {currentStn}]
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
export default TrainInspector;
