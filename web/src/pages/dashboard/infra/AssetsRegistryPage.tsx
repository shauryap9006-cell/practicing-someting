import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { Wrench, ShieldAlert, CheckCircle, Activity, Filter, AlertTriangle } from 'lucide-react';

interface AssetRecord {
  id: string;
  type: string;
  location: string;
  station: string;
  install_date: string;
  condition: string;
  mtbf_hours: number;
  status: 'OPERATIONAL' | 'UNDER_WATCH' | 'MAINTENANCE_DUE';
}

export function AssetsRegistryPage() {
  const [assets, setAssets] = useState<AssetRecord[]>([]);
  const [selectedAsset, setSelectedAsset] = useState<AssetRecord | null>(null);
  const [typeFilter, setTypeFilter] = useState('ALL');

  useEffect(() => {
    api.getAssets().then(data => {
      setAssets(data as AssetRecord[]);
      if (data.length > 0) setSelectedAsset(data[0] as AssetRecord);
    });
  }, []);

  const filtered = assets.filter(
    a => typeFilter === 'ALL' || a.type.toLowerCase().includes(typeFilter.toLowerCase())
  );

  return (
    <div className="space-y-4 font-mono text-xs">
      <SEO title="Infrastructure Assets Registry & MTBF Analytics · RailTwin-X" noindex />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <Wrench className="w-4 h-4 text-[#FFB224]" />
            <span>Infrastructure Asset Registry & MTBF Reliability Analytics</span>
          </h1>
          <p className="text-[#9A9DA3]">
            Track point machines, 4-aspect signals, AF track circuits, and 25kV traction catenary masts
          </p>
        </div>

        {/* Filter */}
        <div className="flex items-center gap-2">
          <select
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value)}
            className="bg-[#15171A] border border-[#26282C] text-[#E8E8E6] p-1.5 focus:outline-none"
          >
            <option value="ALL">All Asset Types</option>
            <option value="Point Machine">Point Machines</option>
            <option value="Signal">Signals</option>
            <option value="Track Circuit">Track Circuits</option>
            <option value="OHE">25kV OHE Masts</option>
          </select>
        </div>
      </div>

      {/* Main Grid: Assets Table & Asset Inspector / Worst 5 MTBF */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Assets Table */}
        <div className="lg:col-span-8 bg-[#15171A] border border-[#26282C] p-4">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#26282C] bg-[#1B1D21] text-[#9A9DA3] text-[11px] uppercase">
                  <th className="py-2.5 px-3">Asset ID</th>
                  <th className="py-2.5 px-3">Equipment Type</th>
                  <th className="py-2.5 px-3">Location / Station</th>
                  <th className="py-2.5 px-3 text-center">MTBF (Hours)</th>
                  <th className="py-2.5 px-3 text-center">Condition</th>
                  <th className="py-2.5 px-3 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#26282C]">
                {filtered.map(a => {
                  const isSelected = selectedAsset?.id === a.id;
                  return (
                    <tr
                      key={a.id}
                      onClick={() => setSelectedAsset(a)}
                      className={`cursor-pointer transition-colors ${
                        isSelected ? 'bg-[#1B1D21] text-[#E8E8E6]' : 'hover:bg-[#1B1D21]/50 text-[#E8E8E6]'
                      }`}
                    >
                      <td className="py-3 px-3 font-bold text-[#FFB224]">{a.id}</td>
                      <td className="py-3 px-3 font-semibold">{a.type}</td>
                      <td className="py-3 px-3 text-[#9A9DA3]">{a.location}</td>
                      <td className="py-3 px-3 text-center font-bold">{a.mtbf_hours.toLocaleString()} hrs</td>
                      <td className="py-3 px-3 text-center">
                        <span className="text-[10px] text-[#9A9DA3]">{a.condition}</span>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <span
                          className={`text-[10px] px-2 py-0.5 border font-bold ${
                            a.status === 'OPERATIONAL'
                              ? 'border-[#3ECF8E] text-[#3ECF8E] bg-[#3ECF8E]/10'
                              : 'border-[#FFB224] text-[#FFB224] bg-[#FFB224]/10'
                          }`}
                        >
                          {a.status.replace('_', ' ')}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Asset Inspector & Worst MTBF Ranking */}
        <div className="lg:col-span-4 space-y-4">
          {/* Asset Inspector */}
          <div className="bg-[#15171A] border border-[#26282C] p-5 space-y-4">
            <div className="font-bold text-sm text-[#E8E8E6] border-b border-[#26282C] pb-2 uppercase">
              Asset Reliability Inspector
            </div>

            {selectedAsset ? (
              <div className="space-y-4">
                <div>
                  <span className="text-[10px] text-[#9A9DA3] uppercase block">Equipment Tag</span>
                  <div className="font-bold text-sm text-[#E8E8E6]">{selectedAsset.id}</div>
                  <div className="text-xs text-[#9A9DA3]">{selectedAsset.type}</div>
                </div>

                <div className="grid grid-cols-2 gap-3 bg-[#0E0F11] p-3 border border-[#26282C]">
                  <div>
                    <span className="text-[10px] text-[#9A9DA3] block uppercase">MTBF Reliability</span>
                    <span className="font-bold text-base text-[#FFB224]">{selectedAsset.mtbf_hours} hrs</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[#9A9DA3] block uppercase">Install Date</span>
                    <span className="font-semibold text-xs text-[#E8E8E6]">{selectedAsset.install_date}</span>
                  </div>
                </div>

                <div className="pt-2 border-t border-[#26282C] space-y-2 text-[11px] text-[#9A9DA3]">
                  <div className="flex justify-between">
                    <span>Geographic Station:</span>
                    <span className="text-[#E8E8E6]">{selectedAsset.station}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Statutory Inspection Cycle:</span>
                    <span className="text-[#3ECF8E]">90-Day POH Cycle (COMPLIANT)</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Failure Risk Index:</span>
                    <span className="text-[#3ECF8E]">0.04 (Low Probability)</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-[#9A9DA3] py-8 text-center">Select an asset to view specs.</div>
            )}
          </div>

          {/* Worst Assets Ranking */}
          <div className="bg-[#15171A] border border-[#26282C] p-4 space-y-2">
            <div className="font-bold text-xs text-[#F0533A] flex items-center gap-1.5 border-b border-[#26282C] pb-1.5">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Lowest MTBF Repeat-Offenders</span>
            </div>
            <div className="space-y-1.5 text-[11px]">
              <div className="flex justify-between py-1 border-b border-[#1B1D21]">
                <span className="text-[#E8E8E6]">AST-TC-44 (Panki West TC)</span>
                <span className="text-[#F0533A] font-bold">1,450 hrs</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1B1D21]">
                <span className="text-[#E8E8E6]">AST-PNT-14B (Cross 14B)</span>
                <span className="text-[#FFB224] font-bold">4,200 hrs</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-[#E8E8E6]">AST-SIG-4A (CNB Home)</span>
                <span className="text-[#3ECF8E] font-bold">8,900 hrs</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
