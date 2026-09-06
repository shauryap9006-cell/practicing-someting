import React from 'react';
import { Link } from 'react-router-dom';
import { SectionShell } from '../primitives';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="max-w-xl mx-auto w-full p-6 py-16 flex flex-col gap-6">
      <SectionShell microLabel="HTTP 404 · Section Anomaly" title="Corridor Route Not Found">
        <div className="flex flex-col gap-4">
          <p className="font-sans text-sm text-ink/80 leading-relaxed">
            The requested track section, operational checkpoint, or train service does not exist
            in the RailTwin-X corridor twin registry.
          </p>

          <div className="flex flex-col gap-2 pt-2 border-t border-line/60">
            <span className="font-mono text-xs text-muted uppercase">Navigate to Active Surfaces:</span>
            <div className="flex flex-wrap gap-2">
              <Link
                to="/t"
                className="font-mono text-xs px-3 py-1.5 rounded-[3px] bg-ink text-surface font-semibold hover:bg-ink/90 transition-colors"
              >
                Train Tracker →
              </Link>
              <Link
                to="/network"
                className="font-mono text-xs px-3 py-1.5 rounded-[3px] bg-surface border border-line text-ink hover:bg-raised transition-colors"
              >
                Corridor Twin
              </Link>
              <Link
                to="/compare"
                className="font-mono text-xs px-3 py-1.5 rounded-[3px] bg-surface border border-line text-ink hover:bg-raised transition-colors"
              >
                Shock Lab
              </Link>
              <Link
                to="/proof"
                className="font-mono text-xs px-3 py-1.5 rounded-[3px] bg-surface border border-line text-ink hover:bg-raised transition-colors"
              >
                Model Proof
              </Link>
            </div>
          </div>
        </div>
      </SectionShell>
    </div>
  );
};
