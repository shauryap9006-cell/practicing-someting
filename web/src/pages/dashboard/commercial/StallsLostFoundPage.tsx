import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { Store, Package, CheckCircle, AlertTriangle, Trash2, UserCheck } from 'lucide-react';
import { toast } from 'sonner';

interface StallRecord {
  id: string;
  name: string;
  platform: string;
  category: string;
  lease_holder: string;
  expiry_date: string;
  days_left: number;
  status: string;
}

interface LostFoundRecord {
  id: string;
  item_name: string;
  found_location: string;
  found_date: string;
  status: 'STORED' | 'RETURNED' | 'DISPOSED';
  claimant?: string | null;
}

export function StallsLostFoundPage() {
  const [activeTab, setActiveTab] = useState<'stalls' | 'lost_found'>('stalls');
  const [stalls, setStalls] = useState<StallRecord[]>([]);
  const [lostItems, setLostItems] = useState<LostFoundRecord[]>([]);

  useEffect(() => {
    api.getStalls().then(data => setStalls(data as StallRecord[]));
    api.getLostFound().then(data => setLostItems(data as LostFoundRecord[]));
  }, []);

  const handleRenewStall = (id: string) => {
    setStalls(prev =>
      prev.map(s => (s.id === id ? { ...s, days_left: 365, status: 'ACTIVE' } : s))
    );
    toast.success(`Lease for ${id} renewed for 12 months.`);
  };

  const handleClaimItem = (id: string) => {
    setLostItems(prev =>
      prev.map(item =>
        item.id === id ? { ...item, status: 'RETURNED', claimant: 'Passenger Claimed (ID Verified)' } : item
      )
    );
    toast.success(`Lost item ${id} marked as returned to passenger.`);
  };

  return (
    <div className="space-y-4 font-mono text-xs">
      <SEO title="Commercial Stalls & Lost & Found · RailTwin-X" noindex />

      {/* Header & Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <Store className="w-4 h-4 text-[#FFB224]" />
            <span>Commercial Stall Leases & Lost & Found Register</span>
          </h1>
          <p className="text-[#9A9DA3]">
            Station concessionaire contracts, lease expiries, and passenger property tracking
          </p>
        </div>

        {/* Tab Selector */}
        <div className="flex items-center gap-1 bg-[#15171A] p-1 border border-[#26282C]">
          <button
            onClick={() => setActiveTab('stalls')}
            className={`px-3 py-1 text-xs transition-colors ${
              activeTab === 'stalls' ? 'bg-[#FFB224] text-[#0E0F11] font-bold' : 'text-[#9A9DA3]'
            }`}
          >
            Platform Stall Leases
          </button>
          <button
            onClick={() => setActiveTab('lost_found')}
            className={`px-3 py-1 text-xs transition-colors ${
              activeTab === 'lost_found' ? 'bg-[#FFB224] text-[#0E0F11] font-bold' : 'text-[#9A9DA3]'
            }`}
          >
            Lost & Found Register
          </button>
        </div>
      </div>

      {activeTab === 'stalls' ? (
        /* Stall Leases Table */
        <div className="bg-[#15171A] border border-[#26282C] p-4">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#26282C] bg-[#1B1D21] text-[#9A9DA3] text-[11px] uppercase">
                  <th className="py-2.5 px-3">Stall ID</th>
                  <th className="py-2.5 px-3">Concession Name</th>
                  <th className="py-2.5 px-3">Location</th>
                  <th className="py-2.5 px-3">Category</th>
                  <th className="py-2.5 px-3">Lease Holder</th>
                  <th className="py-2.5 px-3">Expiry Date</th>
                  <th className="py-2.5 px-3 text-center">Days Left</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#26282C]">
                {stalls.map(s => (
                  <tr key={s.id} className="hover:bg-[#1B1D21]/50 text-[#E8E8E6]">
                    <td className="py-3 px-3 font-bold text-[#FFB224]">{s.id}</td>
                    <td className="py-3 px-3 font-semibold">{s.name}</td>
                    <td className="py-3 px-3 text-[#9A9DA3]">{s.platform}</td>
                    <td className="py-3 px-3">{s.category}</td>
                    <td className="py-3 px-3 text-[#9A9DA3]">{s.lease_holder}</td>
                    <td className="py-3 px-3">{s.expiry_date}</td>
                    <td className="py-3 px-3 text-center">
                      <span
                        className={`text-[10px] px-2 py-0.5 border font-bold ${
                          s.days_left <= 7
                            ? 'border-[#F0533A] text-[#F0533A] bg-[#F0533A]/10'
                            : s.days_left <= 30
                            ? 'border-[#FFB224] text-[#FFB224] bg-[#FFB224]/10'
                            : 'border-[#3ECF8E] text-[#3ECF8E] bg-[#3ECF8E]/10'
                        }`}
                      >
                        {s.days_left} Days
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right">
                      <button
                        onClick={() => handleRenewStall(s.id)}
                        className="text-[#FFB224] hover:underline"
                      >
                        Renew Lease &rarr;
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* Lost & Found Register */
        <div className="bg-[#15171A] border border-[#26282C] p-4">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#26282C] bg-[#1B1D21] text-[#9A9DA3] text-[11px] uppercase">
                  <th className="py-2.5 px-3">Item ID</th>
                  <th className="py-2.5 px-3">Item Description</th>
                  <th className="py-2.5 px-3">Found Location</th>
                  <th className="py-2.5 px-3">Found Date</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Claimant Details</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#26282C]">
                {lostItems.map(item => (
                  <tr key={item.id} className="hover:bg-[#1B1D21]/50 text-[#E8E8E6]">
                    <td className="py-3 px-3 font-bold text-[#FFB224]">{item.id}</td>
                    <td className="py-3 px-3 font-semibold">{item.item_name}</td>
                    <td className="py-3 px-3 text-[#9A9DA3]">{item.found_location}</td>
                    <td className="py-3 px-3">{item.found_date}</td>
                    <td className="py-3 px-3">
                      <span
                        className={`text-[10px] px-2 py-0.5 border font-bold ${
                          item.status === 'STORED'
                            ? 'border-[#FFB224] text-[#FFB224] bg-[#FFB224]/10'
                            : item.status === 'RETURNED'
                            ? 'border-[#3ECF8E] text-[#3ECF8E] bg-[#3ECF8E]/10'
                            : 'border-[#9A9DA3] text-[#9A9DA3]'
                        }`}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-[#9A9DA3]">{item.claimant || 'Unclaimed in Station Custody'}</td>
                    <td className="py-3 px-3 text-right">
                      {item.status === 'STORED' && (
                        <button
                          onClick={() => handleClaimItem(item.id)}
                          className="text-[#3ECF8E] hover:underline"
                        >
                          Verify & Return &rarr;
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
