import React from 'react';
import type { LiveOperationalEvent } from '../lib/types';

interface EventTickerProps {
  events: LiveOperationalEvent[];
}

export const EventTicker: React.FC<EventTickerProps> = ({ events }) => {
  const displayEvents = events.slice(0, 6);

  const getBadgeStyle = (type: string) => {
    switch (type) {
      case 'departure':
        return {
          bg: 'var(--signal-green-wash)',
          color: 'var(--signal-green)',
          border: 'rgba(61, 220, 151, 0.35)',
          label: 'DEP CLEAR',
        };
      case 'arrival':
        return {
          bg: 'var(--ochre-wash)',
          color: 'var(--ochre)',
          border: 'var(--line-ochre)',
          label: 'BERTH ARR',
        };
      case 'delay_shift':
        return {
          bg: 'var(--signal-amber-wash)',
          color: 'var(--signal-amber)',
          border: 'rgba(245, 165, 36, 0.35)',
          label: 'DELAY SHIFT',
        };
      case 'shock':
      case 'alert':
        return {
          bg: 'var(--signal-red-wash)',
          color: 'var(--signal-red)',
          border: 'rgba(244, 80, 106, 0.45)',
          label: 'EMERGENCY',
        };
      case 'tsr':
        return {
          bg: 'var(--ochre-wash)',
          color: 'var(--ochre)',
          border: 'var(--line-ochre)',
          label: 'TSR CAUTION',
        };
      default:
        return {
          bg: 'rgba(100, 116, 139, 0.15)',
          color: '#9E9B93',
          border: 'var(--line-subtle)',
          label: 'DISPATCH',
        };
    }
  };

  const formatTimestamp = (ts: string) => {
    try {
      if (ts.includes('T')) {
        return ts.split('T')[1].slice(0, 8);
      }
      return ts.slice(11, 19) || ts;
    } catch {
      return ts;
    }
  };

  return (
    <div className="event-ticker-panel">
      {/* Panel Header */}
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: 'var(--signal-amber)' }}>[LIVE] DISPATCH</span>
          <span style={{ color: 'var(--text-dim)' }}>&bull;</span>
          <span style={{ color: 'var(--text-primary)' }}>OPERATIONAL CORRIDOR LOG</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span className="status-dot live" style={{ width: '6px', height: '6px' }} />
          <span style={{ fontSize: '9.5px', color: 'var(--text-dim)' }}>REALTIME OCC</span>
        </div>
      </div>

      {/* Ticker Items List */}
      <div className="ticker-list">
        {displayEvents.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '28px 0', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: '10.5px' }}>
            AWAITING OPERATIONAL DISPATCH &amp; SIGNAL EVENTS...
          </div>
        ) : (
          displayEvents.map((ev, idx) => {
            const badge = getBadgeStyle(ev.type);
            const timeFormatted = formatTimestamp(ev.ts);

            return (
              <div key={`${ev.ts}-${idx}`} className="ticker-item">
                <span className="ticker-ts">{timeFormatted}</span>
                <span
                  className="ticker-badge"
                  style={{
                    backgroundColor: badge.bg,
                    color: badge.color,
                    border: `1px solid ${badge.border}`,
                  }}
                >
                  {badge.label}
                </span>
                <span className="ticker-detail" title={ev.detail}>
                  {ev.train_no && (
                    <span style={{ color: 'var(--kiosk-gold)', fontWeight: 700, marginRight: '6px' }}>
                      #{ev.train_no}
                    </span>
                  )}
                  {ev.detail}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
