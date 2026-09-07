import React from 'react';

interface SynapticConnectionsProps {
  pulseSpeed?: number;
  intensity?: number;
}

export const SynapticConnections: React.FC<SynapticConnectionsProps> = ({
  pulseSpeed = 2,
  intensity = 0.5,
}) => {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden z-0 opacity-35 transition-opacity">
      <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 1200 400">
        <defs>
          <linearGradient id="flowGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#C25E00" stopOpacity="0.8" />
            <stop offset="35%" stopColor="#1B6B3A" stopOpacity="0.9" />
            <stop offset="70%" stopColor="#2563eb" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#7c3aed" stopOpacity="0.8" />
          </linearGradient>
        </defs>

        <style>{`
          @keyframes synapticFlow {
            from { stroke-dashoffset: 60; }
            to { stroke-dashoffset: 0; }
          }
          .synapse-line {
            animation: synapticFlow ${pulseSpeed}s linear infinite;
          }
        `}</style>

        <g stroke="url(#flowGrad)" strokeWidth="1.5" fill="none" opacity={intensity}>
          {/* Stage 1 to 2 */}
          <path d="M 210 90 C 250 90, 260 120, 290 120" strokeDasharray="6, 6" className="synapse-line" />
          <path d="M 210 160 C 250 160, 260 170, 290 170" strokeDasharray="6, 6" className="synapse-line" />
          <path d="M 210 230 C 250 230, 260 210, 290 210" strokeDasharray="6, 6" className="synapse-line" />
          <path d="M 210 300 C 250 300, 260 250, 290 250" strokeDasharray="6, 6" className="synapse-line" />

          {/* Stage 2 to 3 */}
          <path d="M 430 120 C 470 120, 480 100, 520 100" strokeDasharray="6, 6" className="synapse-line" />
          <path d="M 430 170 C 470 170, 480 160, 520 160" strokeDasharray="6, 6" className="synapse-line" />
          <path d="M 430 210 C 470 210, 480 220, 520 220" strokeDasharray="6, 6" className="synapse-line" />
          <path d="M 430 250 C 470 250, 480 280, 520 280" strokeDasharray="6, 6" className="synapse-line" />

          {/* Stage 3 Internal Crossings */}
          <path d="M 660 100 C 690 100, 700 140, 730 140" strokeDasharray="4, 4" className="synapse-line" stroke="#2563eb" strokeWidth="2" />
          <path d="M 660 160 C 690 160, 700 170, 730 170" strokeDasharray="4, 4" className="synapse-line" stroke="#1B6B3A" strokeWidth="2" />
          <path d="M 660 220 C 690 220, 700 200, 730 200" strokeDasharray="4, 4" className="synapse-line" stroke="#7c3aed" strokeWidth="2" />
          <path d="M 660 280 C 690 280, 700 230, 730 230" strokeDasharray="4, 4" className="synapse-line" stroke="#C25E00" strokeWidth="2" />

          {/* Stage 3 to 4 */}
          <path d="M 870 140 C 900 140, 910 160, 940 160" strokeDasharray="6, 6" className="synapse-line" stroke="#1B6B3A" />
          <path d="M 870 200 C 900 200, 910 210, 940 210" strokeDasharray="6, 6" className="synapse-line" stroke="#B3362B" />

          {/* Stage 4 to 5 */}
          <path d="M 1030 160 C 1060 160, 1070 175, 1100 175" strokeDasharray="6, 6" className="synapse-line" stroke="#C25E00" strokeWidth="2" />
          <path d="M 1030 210 C 1060 210, 1070 195, 1100 195" strokeDasharray="6, 6" className="synapse-line" stroke="#C25E00" strokeWidth="2" />
        </g>
      </svg>
    </div>
  );
};
