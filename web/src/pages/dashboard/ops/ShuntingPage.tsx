import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { Truck, AlertTriangle, CheckCircle, Plus, Clock } from 'lucide-react';
import { toast } from 'sonner';

interface ShuntMove {
  id: string;
  move_type: string;
  rake_id: string;
  from_track: string;
  to_track: string;
  window: string;
  status: 'OK' | 'FLAGGED';
  logged_by: string;
}

export function ShuntingPage() {
  const [moves, setMoves] = useState<ShuntMove[]>([]);
  const [moveType, setMoveType] = useState('Loco Reversal');
  const [rakeId, setRakeId] = useState('RAKE-DLI-SHT-05');
  const [fromTrack, setFromTrack] = useState('PF 3');
  const [toTrack, setToTrack] = useState('Siding 2');
  const [windowTime, setWindowTime] = useState('18:45 – 19:05');
  const [overrideReason, setOverrideReason] = useState('');
  const [hasConflict, setHasConflict] = useState(false);

  useEffect(() => {
    api.getShuntingMoves().then(data => setMoves(data as ShuntMove[]));
  }, []);

  // Check conflicts dynamically when fromTrack or window changes
  useEffect(() => {
    if (fromTrack === 'PF 3' || fromTrack === 'PF 1') {
      setHasConflict(true);
    } else {
      setHasConflict(false);
    }
  }, [fromTrack, windowTime]);

  const handleLogMove = async (e: React.FormEvent) => {
    e.preventDefault();
    if (hasConflict && !overrideReason.trim()) {
      toast.error('Override reason required for main-line platform window conflicts.');
      return;
    }

    const newMove: ShuntMove = {
      id: `SHT-${Math.floor(10 + Math.random() * 90)}`,
      move_type: moveType,
      rake_id: rakeId,
      from_track: fromTrack,
      to_track: toTrack,
      window: windowTime,
      status: hasConflict ? 'FLAGGED' : 'OK',
      logged_by: 'SM-CNB (Station Master)',
    };

    try {
      await api.logShuntingMove(newMove as unknown as Record<string, unknown>);
      setMoves([newMove, ...moves]);
      toast.success('Shunting move logged successfully.');
      setOverrideReason('');
    } catch {
      toast.error('Failed to log shunting move.');
    }
  };

  return (
    <div className="space-y-4">
      <SEO title="Shunting & Loco Movements Log · RailTwin-X" noindex />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <Truck className="w-4 h-4 text-[#FFB224]" />
            <span>Shunting & Loco Movement Log</span>
          </h1>
          <p className="font-mono text-xs text-[#9A9DA3]">
            Track non-timetable movements to prevent silent platform and loop line conflicts
          </p>
        </div>
      </div>

      {/* Top: Log Shunt Move Form */}
      <div className="bg-[#15171A] border border-[#26282C] p-5 font-mono text-xs">
        <div className="text-sm font-semibold text-[#E8E8E6] mb-3 flex items-center gap-2">
          <Plus className="w-4 h-4 text-[#FFB224]" />
          <span>Log Shunting / Loco Movement</span>
        </div>

        <form onSubmit={handleLogMove} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className="text-[11px] text-[#9A9DA3] uppercase block mb-1">Movement Type</label>
              <select
                value={moveType}
                onChange={e => setMoveType(e.target.value)}
                className="w-full bg-[#0E0F11] border border-[#26282C] text-[#E8E8E6] p-2 focus:outline-none focus:border-[#FFB224]"
              >
                <option>Loco Reversal</option>
                <option>Rake Stabling</option>
                <option>Yard Shunt</option>
                <option>Coach Attachment</option>
              </select>
            </div>

            <div>
              <label className="text-[11px] text-[#9A9DA3] uppercase block mb-1">Rake / Loco ID</label>
              <input
                type="text"
                value={rakeId}
                onChange={e => setRakeId(e.target.value)}
                className="w-full bg-[#0E0F11] border border-[#26282C] text-[#E8E8E6] p-2 focus:outline-none focus:border-[#FFB224]"
              />
            </div>

            <div>
              <label className="text-[11px] text-[#9A9DA3] uppercase block mb-1">From Track &rarr; To Track</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={fromTrack}
                  onChange={e => setFromTrack(e.target.value)}
                  className="w-1/2 bg-[#0E0F11] border border-[#26282C] text-[#E8E8E6] p-2 focus:outline-none focus:border-[#FFB224]"
                />
                <input
                  type="text"
                  value={toTrack}
                  onChange={e => setToTrack(e.target.value)}
                  className="w-1/2 bg-[#0E0F11] border border-[#26282C] text-[#E8E8E6] p-2 focus:outline-none focus:border-[#FFB224]"
                />
              </div>
            </div>

            <div>
              <label className="text-[11px] text-[#9A9DA3] uppercase block mb-1">Time Window (IST)</label>
              <input
                type="text"
                value={windowTime}
                onChange={e => setWindowTime(e.target.value)}
                className="w-full bg-[#0E0F11] border border-[#26282C] text-[#E8E8E6] p-2 focus:outline-none focus:border-[#FFB224]"
              />
            </div>
          </div>

          {/* Conflict Warning Banner */}
          {hasConflict && (
            <div className="bg-[#FFB224]/10 border border-[#FFB224] p-3 text-[#FFB224] space-y-2">
              <div className="flex items-center gap-2 font-bold">
                <AlertTriangle className="w-4 h-4 text-[#FFB224]" />
                <span>CONFLICT WARNING: Movement overlaps Train #12302 (PF 3) berthing window (18:50 – 19:20)</span>
              </div>
              <div>
                <label className="text-[11px] uppercase block mb-1">Station Master Override Reason (Required):</label>
                <input
                  type="text"
                  placeholder="e.g. 12302 rescheduled to PF 4 by Dy. SM"
                  value={overrideReason}
                  onChange={e => setOverrideReason(e.target.value)}
                  className="w-full bg-[#0E0F11] border border-[#FFB224] text-[#E8E8E6] p-1.5 focus:outline-none"
                />
              </div>
            </div>
          )}

          <button
            type="submit"
            className="px-4 py-2 bg-[#FFB224] hover:bg-[#E59F1C] text-[#0E0F11] font-bold text-xs font-mono transition-colors"
          >
            Record Shunting Move
          </button>
        </form>
      </div>

      {/* Bottom: Moves Log Table */}
      <div className="bg-[#15171A] border border-[#26282C] p-4">
        <div className="text-xs font-mono font-semibold text-[#E8E8E6] uppercase mb-3">
          Today&apos;s Shunting & Yard Movements Log
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#26282C] bg-[#1B1D21] text-[#9A9DA3] text-[11px] uppercase">
                <th className="py-2 px-3">Move ID</th>
                <th className="py-2 px-3">Type</th>
                <th className="py-2 px-3">Rake / Loco</th>
                <th className="py-2 px-3">Route</th>
                <th className="py-2 px-3">Window</th>
                <th className="py-2 px-3">Logged By</th>
                <th className="py-2 px-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#26282C]">
              {moves.map(m => (
                <tr key={m.id} className="hover:bg-[#1B1D21]/50 text-[#E8E8E6]">
                  <td className="py-2.5 px-3 font-bold text-[#FFB224]">{m.id}</td>
                  <td className="py-2.5 px-3">{m.move_type}</td>
                  <td className="py-2.5 px-3 font-semibold">{m.rake_id}</td>
                  <td className="py-2.5 px-3">{m.from_track} &rarr; {m.to_track}</td>
                  <td className="py-2.5 px-3">{m.window}</td>
                  <td className="py-2.5 px-3 text-[#9A9DA3]">{m.logged_by}</td>
                  <td className="py-2.5 px-3 text-center">
                    <span
                      className={`text-[10px] px-2 py-0.5 border ${
                        m.status === 'OK'
                          ? 'border-[#3ECF8E] text-[#3ECF8E] bg-[#3ECF8E]/10'
                          : 'border-[#FFB224] text-[#FFB224] bg-[#FFB224]/10'
                      }`}
                    >
                      {m.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
