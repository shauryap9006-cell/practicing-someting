import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { AlertCircle, Plus, Search, Filter } from 'lucide-react';
import { toast } from 'sonner';

interface IncidentItem {
  id: string;
  time: string;
  type: string;
  location: string;
  severity: 'critical' | 'major' | 'minor';
  status: 'Open' | 'Investigating' | 'Closed';
  reporter: string;
  description: string;
}

export function IncidentsPage() {
  const [incidents, setIncidents] = useState<IncidentItem[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<IncidentItem | null>(null);
  const [showLogModal, setShowLogModal] = useState(false);
  const [newIncident, setNewIncident] = useState<{
    type: string;
    location: string;
    severity: 'critical' | 'major' | 'minor';
    reporter: string;
    description: string;
  }>({
    type: 'SPAD',
    location: 'CNB West Home Signal',
    severity: 'critical',
    reporter: 'SM-CNB Duty Staff',
    description: 'Driver passed signal 14 at danger due to wheel slip.',
  });

  useEffect(() => {
    api.getIncidents().then(data => {
      setIncidents(data as IncidentItem[]);
      if (data.length > 0) setSelectedIncident(data[0] as IncidentItem);
    });
  }, []);

  const handleLogIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await api.logIncident(newIncident);
      const item: IncidentItem = {
        id: (created as { id: string }).id,
        time: new Date().toLocaleTimeString(),
        type: newIncident.type,
        location: newIncident.location,
        severity: newIncident.severity,
        status: 'Open',
        reporter: newIncident.reporter,
        description: newIncident.description,
      };
      setIncidents([item, ...incidents]);
      setSelectedIncident(item);
      toast.success('Incident logged and safety escalation dispatched.');
      setShowLogModal(false);
    } catch {
      toast.error('Failed to log incident.');
    }
  };

  return (
    <div className="space-y-4">
      <SEO title="Incident & Near-Miss Register · RailTwin-X" noindex />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-[#F0533A]" />
            <span>Incident & Near-Miss Safety Register</span>
          </h1>
          <p className="font-mono text-xs text-[#9A9DA3]">
            SPAD, Equipment Failures, OHE Tripping, and Track Obstruction Ledger
          </p>
        </div>

        <button
          onClick={() => setShowLogModal(true)}
          className="px-3 py-1.5 bg-[#F0533A] hover:bg-[#D43F28] text-[#E8E8E6] font-mono font-bold text-xs flex items-center gap-1.5 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Log Safety Incident</span>
        </button>
      </div>

      {/* Incidents Table & Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-8 bg-[#15171A] border border-[#26282C] p-4">
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#26282C] bg-[#1B1D21] text-[#9A9DA3] text-[11px] uppercase">
                  <th className="py-2.5 px-3">Incident ID</th>
                  <th className="py-2.5 px-3">Time</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Location</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Reporter</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#26282C]">
                {incidents.map(inc => {
                  const isSelected = selectedIncident?.id === inc.id;
                  const severityBorder =
                    inc.severity === 'critical'
                      ? 'border-l-4 border-l-[#F0533A]'
                      : inc.severity === 'major'
                      ? 'border-l-4 border-l-[#FFB224]'
                      : 'border-l-4 border-l-[#3ECF8E]';

                  return (
                    <tr
                      key={inc.id}
                      onClick={() => setSelectedIncident(inc)}
                      className={`cursor-pointer transition-colors ${severityBorder} ${
                        isSelected ? 'bg-[#1B1D21] text-[#E8E8E6]' : 'hover:bg-[#1B1D21]/50 text-[#E8E8E6]'
                      }`}
                    >
                      <td className="py-3 px-3 font-bold text-[#FFB224]">{inc.id}</td>
                      <td className="py-3 px-3 text-[#9A9DA3]">{inc.time}</td>
                      <td className="py-3 px-3 font-semibold">{inc.type}</td>
                      <td className="py-3 px-3">{inc.location}</td>
                      <td className="py-3 px-3">
                        <span
                          className={`text-[10px] px-1.5 py-0.5 border ${
                            inc.status === 'Open'
                              ? 'border-[#F0533A] text-[#F0533A] bg-[#F0533A]/10'
                              : inc.status === 'Investigating'
                              ? 'border-[#FFB224] text-[#FFB224] bg-[#FFB224]/10'
                              : 'border-[#3ECF8E] text-[#3ECF8E]'
                          }`}
                        >
                          {inc.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-[#9A9DA3]">{inc.reporter}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Incident Drawer */}
        <div className="lg:col-span-4 bg-[#15171A] border border-[#26282C] p-5 font-mono text-xs space-y-4">
          <div className="border-b border-[#26282C] pb-2 font-bold text-sm text-[#E8E8E6] uppercase">
            Incident Investigation Summary
          </div>

          {selectedIncident ? (
            <div className="space-y-4">
              <div>
                <span className="text-[10px] text-[#9A9DA3] uppercase block">Incident ID & Severity</span>
                <div className="flex items-center gap-2 mt-1">
                  <span className="font-bold text-sm text-[#E8E8E6]">{selectedIncident.id}</span>
                  <span
                    className={`text-[10px] font-bold uppercase px-2 py-0.5 border ${
                      selectedIncident.severity === 'critical'
                        ? 'border-[#F0533A] text-[#F0533A] bg-[#F0533A]/10'
                        : 'border-[#FFB224] text-[#FFB224] bg-[#FFB224]/10'
                    }`}
                  >
                    {selectedIncident.severity}
                  </span>
                </div>
              </div>

              <div className="bg-[#0E0F11] p-3 border border-[#26282C] space-y-2">
                <div>
                  <span className="text-[10px] text-[#9A9DA3] uppercase block">Location</span>
                  <span className="font-semibold text-xs text-[#E8E8E6]">{selectedIncident.location}</span>
                </div>
                <div>
                  <span className="text-[10px] text-[#9A9DA3] uppercase block">Description</span>
                  <p className="text-xs text-[#E8E8E6] mt-0.5">{selectedIncident.description}</p>
                </div>
              </div>

              <div className="pt-2 border-t border-[#26282C] space-y-2 text-[11px] text-[#9A9DA3]">
                <div className="flex justify-between">
                  <span>Reported By:</span>
                  <span className="text-[#E8E8E6]">{selectedIncident.reporter}</span>
                </div>
                <div className="flex justify-between">
                  <span>Safety Division Notified:</span>
                  <span className="text-[#3ECF8E]">NCR Safety Cell (ACKNOWLEDGED)</span>
                </div>
                <div className="flex justify-between">
                  <span>Delay Autopsy Link:</span>
                  <span className="text-[#FFB224]">Included in Root-Cause Causality</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-[#9A9DA3] py-8 text-center">Select an incident to view details.</div>
          )}
        </div>
      </div>

      {/* Log Modal */}
      {showLogModal && (
        <div className="fixed inset-0 z-50 bg-[#0E0F11]/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#15171A] border border-[#26282C] max-w-md w-full p-6 font-mono text-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[#26282C] pb-3">
              <span className="text-sm font-bold text-[#E8E8E6]">Log Safety Incident / Near-Miss</span>
              <button onClick={() => setShowLogModal(false)} className="text-[#9A9DA3] hover:text-[#E8E8E6]">✕</button>
            </div>

            <form onSubmit={handleLogIncident} className="space-y-3">
              <div>
                <label className="text-[10px] text-[#9A9DA3] block mb-1">Incident Type</label>
                <select
                  value={newIncident.type}
                  onChange={e => setNewIncident({ ...newIncident, type: e.target.value })}
                  className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
                >
                  <option>SPAD (Signal Passed at Danger)</option>
                  <option>Track Circuit Glitch</option>
                  <option>OHE Tripping (25kV)</option>
                  <option>Passenger Injury / Medical</option>
                  <option>Near Miss / Cattle Trespass</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] text-[#9A9DA3] block mb-1">Location</label>
                <input
                  type="text"
                  value={newIncident.location}
                  onChange={e => setNewIncident({ ...newIncident, location: e.target.value })}
                  className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
                />
              </div>

              <div>
                <label className="text-[10px] text-[#9A9DA3] block mb-1">Severity Level</label>
                <select
                  value={newIncident.severity}
                  onChange={e => setNewIncident({ ...newIncident, severity: e.target.value as 'critical' | 'major' | 'minor' })}
                  className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
                >
                  <option value="critical">Critical (Immediate Stop)</option>
                  <option value="major">Major (Caution Required)</option>
                  <option value="minor">Minor (Investigation Only)</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] text-[#9A9DA3] block mb-1">Description & Immediate Action</label>
                <textarea
                  rows={3}
                  value={newIncident.description}
                  onChange={e => setNewIncident({ ...newIncident, description: e.target.value })}
                  className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
                />
              </div>

              <div className="pt-3 border-t border-[#26282C] flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowLogModal(false)}
                  className="px-3 py-1.5 bg-[#1B1D21] border border-[#26282C] text-[#9A9DA3]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-[#F0533A] text-[#E8E8E6] font-bold"
                >
                  Log & Dispatch Alert
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
