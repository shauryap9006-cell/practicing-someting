import React from 'react';
import type { NetworkState } from '../lib/types';
import { getDelayStatusBadge } from '../lib/motion';

interface TrainChipsProps {
  network: NetworkState | null;
  selectedTrainNo?: string | null;
  onSelectTrain?: (trainNo: string) => void;
}

export const TrainChips: React.FC<TrainChipsProps> = ({
  network,
  selectedTrainNo,
  onSelectTrain,
}) => {
  const trains = network?.trains || [];

  if (trains.length === 0) {
    return (
      <div className="train-chips-strip" style={{ justifyContent: 'center' }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-dim)', letterSpacing: '0.8px' }}>
          ACQUIRING LIVE FLEET CORRIDOR TELEMETRY &bull; 1 HZ KINEMATIC STREAM…
        </span>
      </div>
    );
  }

  // Double the list for seamless continuous infinite marquee
  const displayList = trains.length > 8 ? [...trains, ...trains] : trains;

  const getTrainCategory = (name: string, trainNo: string) => {
    const n = name.toUpperCase();
    if (n.includes('VANDE BHARAT')) return 'VB';
    if (n.includes('RAJDHANI')) return 'RAJ';
    if (n.includes('SHATABDI')) return 'SHT';
    if (n.includes('TEJAS')) return 'TEJ';
    if (n.includes('DURONTO')) return 'DUR';
    if (n.includes('GARIB RATH')) return 'GR';
    if (n.includes('SUPERFAST') || n.includes('SF')) return 'SF';
    if (n.includes('EXPRESS') || n.includes('EXP')) return 'EXP';
    if (parseInt(trainNo, 10) % 2 !== 0) return 'UP-EXP';
    return 'DN-EXP';
  };

  return (
    <div className="train-chips-strip">
      <div className={`marquee-container ${trains.length > 8 ? 'scrolling' : ''}`}>
        {displayList.map((t, idx) => {
          const badge = getDelayStatusBadge(t.current_delay_min);
          const cat = getTrainCategory(t.train_name, t.train_no);
          const isSelected = selectedTrainNo === t.train_no;

          return (
            <div
              key={`${t.train_no}-${idx}`}
              className={`train-chip ${isSelected ? 'active' : ''}`}
              onClick={() => onSelectTrain?.(t.train_no)}
              title={`Click to inspect #${t.train_no} ${t.train_name}`}
            >
              {/* Category pill */}
              <span
                style={{
                  fontSize: '8.5px',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 700,
                  color: 'var(--text-dim)',
                  backgroundColor: 'var(--bg-night-2)',
                  padding: '1px 4px',
                  borderRadius: '2px',
                }}
              >
                {cat}
              </span>

              {/* Train No */}
              <span className="chip-train-no">#{t.train_no}</span>

              {/* Train Name */}
              <span className="chip-train-name" title={t.train_name}>
                {t.train_name.replace(/(Express|Special|Superfast|Passenger|MEMU|Rajdhani|Shatabdi)/gi, '').trim() || t.train_name}
              </span>

              {/* Delay status badge */}
              <span
                className="chip-delay-badge"
                style={{
                  color: badge.color,
                  backgroundColor: badge.bg,
                  border: `1px solid ${badge.border}`,
                }}
              >
                {badge.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
