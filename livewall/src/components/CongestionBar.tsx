import React from 'react';
import type { CongestionRadarData } from '@railtwin/shared-types';

interface CongestionBarProps {
  congestion: CongestionRadarData | null;
}

export const CongestionBar: React.FC<CongestionBarProps> = ({ congestion }) => {
  const sections = congestion?.radar || [];

  const getOccupancyColor = (pct: number) => {
    if (pct < 40) return 'var(--signal-green)';
    if (pct <= 70) return 'var(--signal-amber)';
    return 'var(--signal-red)';
  };

  return (
    <div className="congestion-panel">
      {/* Header / Radar Title */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700, color: 'var(--kiosk-gold)', letterSpacing: '0.8px' }}>
            CORRIDOR BLOCK OCCUPANCY &amp; CAPACITY RADAR
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9.5px', color: 'var(--text-dim)' }}>
            &bull; {sections.length || 7} SECTIONS (AUTOMATIC BLOCK SIGNALING)
          </span>
        </div>
        <div style={{ display: 'flex', gap: '14px', fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-dim)' }}>
          <span style={{ color: 'var(--signal-green)' }}>[&lt;40% CLEAR]</span>
          <span style={{ color: 'var(--signal-amber)' }}>[40-70% MOD]</span>
          <span style={{ color: 'var(--signal-red)' }}>[&gt;70% CRIT]</span>
        </div>
      </div>

      {/* Grid of Sections */}
      <div className="congestion-grid">
        {sections.length === 0 ? (
          <div style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: '10.5px' }}>
            ACQUIRING CORRIDOR BLOCK SIGNALING DATA...
          </div>
        ) : (
          sections.map((sec) => {
            const occ = Math.round(sec.horizons?.h0?.occupancy_pct ?? sec.peak_occupancy_pct ?? 0);
            const activeCount = sec.horizons?.h0?.active_trains ?? 0;
            const color = getOccupancyColor(occ);
            const isCritical = occ > 70;

            // Discrete 10-block track circuit visualization
            const totalBlocks = 10;
            const filledBlocks = Math.min(totalBlocks, Math.round((occ / 100) * totalBlocks));

            return (
              <div key={sec.section_id} className={`section-bar-item ${isCritical ? 'critical' : ''}`}>
                <div className="section-bar-header">
                  <span className="section-name" title={sec.section_name}>
                    {sec.section_id.replace('-', ' -> ')}
                    {isCritical && (
                      <span style={{ color: 'var(--signal-red)', marginLeft: '4px', fontSize: '8.5px', fontFamily: 'var(--font-mono)' }}>
                        [!]
                      </span>
                    )}
                  </span>
                  <span className="section-pct" style={{ color }}>
                    {occ}% <span style={{ fontSize: '8.5px', color: 'var(--text-dim)', fontWeight: 400 }}>({activeCount}T)</span>
                  </span>
                </div>

                {/* 10-Segmented Discrete Track Circuit Block Bar */}
                <div className="track-progress-bar">
                  {Array.from({ length: totalBlocks }).map((_, bIdx) => {
                    const isFilled = bIdx < filledBlocks;
                    return (
                      <div
                        key={bIdx}
                        className="track-block-cell"
                        style={{
                          backgroundColor: isFilled ? color : undefined,
                          boxShadow: isFilled && isCritical ? `0 0 6px ${color}` : undefined,
                        }}
                      />
                    );
                  })}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
