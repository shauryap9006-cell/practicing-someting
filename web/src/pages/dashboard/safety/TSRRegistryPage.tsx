import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { ShieldAlert, Plus, CheckCircle, AlertTriangle, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

interface TSRRecord {
  id: string;
  order_no: string;
  section: string;
  start_km: number;
  end_km: number;
  speed_limit_kmph: number;
  cause: string;
  status: 'ACTIVE' | 'EXPIRED' | 'SCHEDULED';
  effective_from: string;
  effective_to: string;
}

export function TSRRegistryPage() {
  const navigate = useNavigate();
  const [tsrs, setTsrs] = useState<TSRRecord[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newOrder, setNewOrder] = useState({
    from_code: 'CNB',
    to_code: 'ON',
    start_km: 1014.2,
    end_km: 1017.8,
    speed_limit_kmph: 30,
    cause: 'Track renewal and tamping',
  });

  useEffect(() => {
    api.getTSRs().then(data => setTsrs(data as TSRRecord[]));
  }, []);

  const handleLiftTSR = async (id: string) => {
    try {
      await api.liftTSR(id);
      setTsrs(prev => prev.map(t => (t.id === id ? { ...t, status: 'EXPIRED' } : t)));
      toast.success(`Speed restriction ${id} lifted. Corridor line restored.`);
    } catch {
      toast.error('Failed to lift speed restriction.');
    }
  };

  const handleCreateTSR = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await api.createTSR(newOrder);
      setTsrs([
        {
          id: (created as { id: string }).id,
          order_no: `CO-NCR-${newOrder.from_code}-${Math.floor(1000 + Math.random() * 9000)}`,
          section: `${newOrder.from_code} – ${newOrder.to_code}`,
          start_km: newOrder.start_km,
          end_km: newOrder.end_km,
          speed_limit_kmph: newOrder.speed_limit_kmph,
          cause: newOrder.cause,
          status: 'ACTIVE',
          effective_from: new Date().toLocaleString(),
          effective_to: 'Until Further Notice',
        },
        ...tsrs,
      ]);
      toast.success('Temporary Speed Restriction (TSR) issued and broadcast to all trains.');
      setShowAddModal(false);
    } catch {
      toast.error('Failed to create TSR.');
    }
  };

  return (
    <div className="space-y-4">
      <SEO title="TSR / Caution Order Registry · RailTwin-X" noindex />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-[#FFB224]" />
            <span>Temporary Speed Restriction (TSR) & Caution Order Registry</span>
          </h1>
          <p className="font-mono text-xs text-[#9A9DA3]">
            Official Permanent & Temporary Speed Restriction Orders with live ML feature ingestion
          </p>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="px-3 py-1.5 bg-[#FFB224] hover:bg-[#E59F1C] text-[#0E0F11] font-mono font-bold text-xs flex items-center gap-1.5 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Issue New TSR Order</span>
        </button>
      </div>

      {/* TSR Table */}
      <div className="bg-[#15171A] border border-[#26282C] p-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#26282C] bg-[#1B1D21] text-[#9A9DA3] text-[11px] uppercase">
                <th className="py-2.5 px-3">Order No</th>
                <th className="py-2.5 px-3">Section</th>
                <th className="py-2.5 px-3">Chainage KM</th>
                <th className="py-2.5 px-3 text-center">Speed Cap</th>
                <th className="py-2.5 px-3">Cause / Reason</th>
                <th className="py-2.5 px-3">Effective Window</th>
                <th className="py-2.5 px-3 text-center">Status</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#26282C]">
              {tsrs.map(t => (
                <tr key={t.id} className="hover:bg-[#1B1D21]/50 text-[#E8E8E6]">
                  <td className="py-3 px-3 font-bold text-[#FFB224]">{t.order_no}</td>
                  <td className="py-3 px-3 font-semibold">{t.section}</td>
                  <td className="py-3 px-3 text-[#9A9DA3]">KM {t.start_km} – {t.end_km}</td>
                  <td className="py-3 px-3 text-center">
                    <span className="font-bold text-sm bg-[#FFB224]/10 border border-[#FFB224] text-[#FFB224] px-2 py-0.5">
                      {t.speed_limit_kmph} km/h
                    </span>
                  </td>
                  <td className="py-3 px-3">{t.cause}</td>
                  <td className="py-3 px-3 text-[11px] text-[#9A9DA3]">
                    {t.effective_from} &rarr; {t.effective_to}
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span
                      className={`text-[10px] px-2 py-0.5 border font-bold ${
                        t.status === 'ACTIVE'
                          ? 'border-[#FFB224] text-[#FFB224] bg-[#FFB224]/10'
                          : 'border-[#9A9DA3] text-[#9A9DA3]'
                      }`}
                    >
                      {t.status}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right space-x-2">
                    <button
                      onClick={() => navigate('/dashboard/map')}
                      className="text-[#9A9DA3] hover:text-[#E8E8E6] text-[11px]"
                      title="Show on Corridor GIS Map"
                    >
                      Map &rarr;
                    </button>
                    {t.status === 'ACTIVE' && (
                      <button
                        onClick={() => handleLiftTSR(t.id)}
                        className="text-[#3ECF8E] hover:underline text-[11px]"
                      >
                        Lift TSR
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add TSR Modal Dialog */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-[#0E0F11]/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#15171A] border border-[#26282C] max-w-md w-full p-6 font-mono text-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[#26282C] pb-3">
              <span className="text-sm font-bold text-[#E8E8E6]">Issue Caution Order / Speed Restriction</span>
              <button onClick={() => setShowAddModal(false)} className="text-[#9A9DA3] hover:text-[#E8E8E6]">✕</button>
            </div>

            <form onSubmit={handleCreateTSR} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] text-[#9A9DA3] block mb-1">From Station</label>
                  <input
                    type="text"
                    value={newOrder.from_code}
                    onChange={e => setNewOrder({ ...newOrder, from_code: e.target.value })}
                    className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-[#9A9DA3] block mb-1">To Station</label>
                  <input
                    type="text"
                    value={newOrder.to_code}
                    onChange={e => setNewOrder({ ...newOrder, to_code: e.target.value })}
                    className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-[10px] text-[#9A9DA3] block mb-1">Start KM</label>
                  <input
                    type="number"
                    step="0.1"
                    value={newOrder.start_km}
                    onChange={e => setNewOrder({ ...newOrder, start_km: parseFloat(e.target.value) })}
                    className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-[#9A9DA3] block mb-1">End KM</label>
                  <input
                    type="number"
                    step="0.1"
                    value={newOrder.end_km}
                    onChange={e => setNewOrder({ ...newOrder, end_km: parseFloat(e.target.value) })}
                    className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-[#9A9DA3] block mb-1">Speed Cap (km/h)</label>
                  <input
                    type="number"
                    value={newOrder.speed_limit_kmph}
                    onChange={e => setNewOrder({ ...newOrder, speed_limit_kmph: parseInt(e.target.value) })}
                    className="w-full bg-[#0E0F11] border border-[#FFB224] p-2 text-[#FFB224] font-bold"
                  />
                </div>
              </div>

              <div>
                <label className="text-[10px] text-[#9A9DA3] block mb-1">Cause / Operational Reason</label>
                <input
                  type="text"
                  value={newOrder.cause}
                  onChange={e => setNewOrder({ ...newOrder, cause: e.target.value })}
                  className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
                />
              </div>

              <div className="pt-3 border-t border-[#26282C] flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 bg-[#1B1D21] border border-[#26282C] text-[#9A9DA3]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-[#FFB224] text-[#0E0F11] font-bold"
                >
                  Confirm & Broadcast
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
