import React, { useState, useEffect } from 'react';

export const DevPanel: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  // Listen for Shift+S
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.shiftKey && (e.key === 'S' || e.key === 's')) {
        setIsOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const injectEvent = async (type: string, severity: number, station: string, desc: string) => {
    try {
      setFeedback(`Injecting ${type}…`);
      const res = await fetch('/v1/demo/inject-event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: type,
          severity_min: severity,
          station,
          description: desc,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setFeedback(data.message || `Injected ${type} (+${severity}m)`);
      } else {
        setFeedback('Failed to inject event');
      }
    } catch {
      setFeedback('Network error injecting event');
    }
    setTimeout(() => setFeedback(null), 4000);
  };

  const resetEvents = async () => {
    try {
      setFeedback('Resetting operational shocks…');
      const res = await fetch('/v1/demo/reset-events', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setFeedback(data.message || 'Events reset');
      } else {
        setFeedback('Failed to reset');
      }
    } catch {
      setFeedback('Network error resetting');
    }
    setTimeout(() => setFeedback(null), 4000);
  };

  if (!isOpen) return null;

  return (
    <div className="dev-panel">
      <div className="dev-header">
        <span>[DEV] SIMULATION INJECTOR (Shift+S)</span>
        <button
          onClick={() => setIsOpen(false)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-dim)',
            cursor: 'pointer',
            fontSize: '14px',
          }}
        >
          [X]
        </button>
      </div>

      <div className="dev-actions">
        <button
          className="dev-btn"
          onClick={() =>
            injectEvent('WEATHER_FOG', 45, 'CNB', 'Dense fog zero-visibility warning @ Kanpur Central')
          }
        >
          [FOG] Inject Dense Fog (+45m @ CNB)
        </button>

        <button
          className="dev-btn"
          onClick={() =>
            injectEvent('SIGNAL_HOLD', 30, 'GZB', 'Automatic signaling interlock hold @ Ghaziabad')
          }
        >
          [HOLD] Inject Signal Hold (+30m @ GZB)
        </button>

        <button
          className="dev-btn"
          onClick={() =>
            injectEvent('TSR_ACTIVE', 25, 'TDL', 'Emergency track ballast tamp TSR 30 km/h @ Tundla')
          }
        >
          [TSR] Inject Speed Restriction TSR (+25m @ TDL)
        </button>

        <button
          className="dev-btn"
          onClick={() =>
            injectEvent('RAKE_DELAY', 60, 'NDLS', 'Incoming rake maintenance turnaround delay @ New Delhi')
          }
        >
          [RAKE] Inject Rake Deficit Hold (+60m @ NDLS)
        </button>

        <button
          className="dev-btn"
          style={{ borderColor: 'var(--signal-amber)', color: 'var(--signal-amber)', marginTop: '4px' }}
          onClick={resetEvents}
        >
          [RESET] Reset All Injected Demo Events
        </button>
      </div>

      {feedback && (
        <div style={{ marginTop: '10px', fontSize: '10px', color: 'var(--kiosk-gold)' }}>
          {feedback}
        </div>
      )}
    </div>
  );
};
