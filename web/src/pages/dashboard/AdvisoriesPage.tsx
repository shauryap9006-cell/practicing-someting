import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Advisory } from '@/mock/types';
import {
  AspectLamp,
  AspectType,
  Provenance,
  EmptyState,
} from '@/components/aspect';
import {
  AlertTriangle,
  Check,
  X,
  ShieldAlert,
  Clock,
  Sparkles,
  Filter,
  CheckCircle2,
} from 'lucide-react';
import { toast } from 'sonner';

export const AdvisoriesPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: advisories = [], dataUpdatedAt } = useQuery({
    queryKey: queryKeys.advisories(),
    queryFn: () => api.getAdvisories(),
    refetchInterval: 5000,
  });

  const [selectedAdvId, setSelectedAdvId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<'pending' | 'accepted' | 'dismissed' | 'all'>('pending');
  const [reasonModalOpen, setReasonModalOpen] = useState(false);
  const [modalAction, setModalAction] = useState<'accept' | 'dismiss'>('accept');
  const [customReason, setCustomReason] = useState('');

  const acceptMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => api.acceptAdvisory(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.advisories() });
      toast.success('Advisory Accepted & Plan Updated', {
        description: 'New platform routing logged in regulatory audit ledger.',
      });
      setReasonModalOpen(false);
    },
  });

  const dismissMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => api.dismissAdvisory(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.advisories() });
      toast.info('Advisory Dismissed', {
        description: 'Retained current dispatch plan under dispatcher discretion.',
      });
      setReasonModalOpen(false);
    },
  });

  const filteredAdvisories = advisories.filter(a => {
    if (statusFilter === 'all') return true;
    return a.status === statusFilter;
  });

  useEffect(() => {
    if (filteredAdvisories.length > 0 && !selectedAdvId) {
      setSelectedAdvId(filteredAdvisories[0].id);
    }
  }, [filteredAdvisories, selectedAdvId]);

  // Keyboard navigation: A = Accept, D = Dismiss
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement).tagName)) {
        return;
      }

      if (e.key === 'a' || e.key === 'A') {
        e.preventDefault();
        if (selectedAdvId) {
          const adv = advisories.find(a => a.id === selectedAdvId && a.status === 'pending');
          if (adv) openActionModal('accept', adv.id);
        }
      } else if (e.key === 'd' || e.key === 'D') {
        e.preventDefault();
        if (selectedAdvId) {
          const adv = advisories.find(a => a.id === selectedAdvId && a.status === 'pending');
          if (adv) openActionModal('dismiss', adv.id);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedAdvId, advisories]);

  const openActionModal = (action: 'accept' | 'dismiss', id: string) => {
    setSelectedAdvId(id);
    setModalAction(action);
    setCustomReason(
      action === 'accept'
        ? 'Accepted per recommendation; platform berth clearance interlocks confirmed.'
        : 'Dispatcher discretion override: retained existing dispatch plan.'
    );
    setReasonModalOpen(true);
  };

  const handleConfirmAction = () => {
    if (!selectedAdvId) return;
    if (modalAction === 'accept') {
      acceptMutation.mutate({ id: selectedAdvId, reason: customReason });
    } else {
      dismissMutation.mutate({ id: selectedAdvId, reason: customReason });
    }
  };

  const selectedAdv = advisories.find(a => a.id === selectedAdvId);

  const getAspect = (priority: string): AspectType => {
    if (priority === 'danger' || priority === 'high') return 'restrict';
    if (priority === 'warn' || priority === 'medium') return 'caution';
    return 'signal';
  };

  return (
    <div className="space-y-6 font-mono select-none">
      {/* Header & Filter Controls Card */}
      <div className="bg-[#101216] border border-[#23272F] rounded-lg p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-[#23272F]">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#F5A524] shadow-[0_0_8px_rgba(245,165,36,0.6)] animate-pulse" />
              <h1 className="text-lg font-bold text-[#E9EBEE] uppercase tracking-wider font-display">
                ADVISORY TRIAGE QUEUE ({filteredAdvisories.length})
              </h1>
            </div>
            <p className="text-xs font-sans text-[#A3ABB6] mt-1">
              Real-time platform re-optimization, crew reliefs, and speed restriction notifications.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <kbd className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 bg-[#0A0B0D] border border-[#23272F] text-[10px] text-[#A3ABB6] rounded-sm">
              Press [A] to Accept · [D] to Dismiss
            </kbd>
            <div className="text-xs text-[#3DDC97] flex items-center gap-1.5 font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-[#3DDC97] animate-pulse" />
              <span>LIVE</span>
            </div>
          </div>
        </div>

        {/* Status Filter Tabs */}
        <div className="flex items-center gap-2">
          {(['pending', 'accepted', 'dismissed', 'all'] as const).map(st => (
            <button
              key={st}
              type="button"
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-sm border text-xs font-bold uppercase tracking-wider transition-colors ${
                statusFilter === st
                  ? 'bg-[#F5A524] text-[#0A0B0D] border-[#F5A524]'
                  : 'bg-[#0A0B0D] text-[#A3ABB6] border-[#23272F] hover:border-[#2E333D] hover:text-[#E9EBEE]'
              }`}
            >
              {st} ({advisories.filter(a => st === 'all' ? true : a.status === st).length})
            </button>
          ))}
        </div>
      </div>

      {/* Two Column Layout: List Left + Detailed Inspection Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Advisories List Left */}
        <div className="lg:col-span-6 space-y-3">
          {filteredAdvisories.length === 0 ? (
            <EmptyState
              title="No advisories in selected filter"
              description="Switch filter tabs to review historical accepted or dismissed operational advisories."
            />
          ) : (
            filteredAdvisories.map(adv => {
              const isSelected = selectedAdvId === adv.id;
              const aspect = getAspect(adv.priority);

              return (
                <div
                  key={adv.id}
                  onClick={() => setSelectedAdvId(adv.id)}
                  className={`p-4 bg-[#101216] border rounded-lg transition-all duration-120 cursor-pointer space-y-3 ${
                    isSelected
                      ? 'border-[#F5A524] ring-1 ring-[#F5A524] bg-[#15181D]'
                      : 'border-[#23272F] hover:border-[#2E333D] hover:bg-[#15181D]/60'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-xs text-[#E9EBEE]">{adv.code}</span>
                      <span className="text-[10px] text-[#6B7480]">·</span>
                      <span className="text-xs text-[#F5A524] font-bold">{adv.trainNo}</span>
                    </div>

                    <AspectLamp
                      aspect={aspect}
                      label={adv.status === 'pending' ? adv.priority.toUpperCase() : adv.status.toUpperCase()}
                      size="xs"
                    />
                  </div>

                  <p className="text-xs font-sans text-[#E9EBEE] leading-relaxed">
                    {adv.rationale || adv.title}
                  </p>

                  <div className="flex items-center justify-between text-[11px] pt-1 text-[#A3ABB6] border-t border-[#23272F]">
                    <span>Expected Gain: <strong className="text-[#3DDC97]">{adv.simulatedImpact?.delaySavingsMinutes || 12}m Saved</strong></span>
                    <span className="text-[#6B7480]">{adv.createdAt || '17:42 IST'}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Advisory Detail Card Right */}
        <div className="lg:col-span-6">
          {selectedAdv ? (
            <div className="bg-[#101216] border border-[#23272F] rounded-lg p-6 space-y-5 sticky top-16">
              <div className="flex items-center justify-between pb-4 border-b border-[#23272F]">
                <div>
                  <span className="text-[10px] text-[#6B7480] uppercase tracking-wider block">Advisory Protocol</span>
                  <h2 className="text-base font-bold text-[#E9EBEE] mt-0.5">{selectedAdv.code}</h2>
                </div>

                <AspectLamp aspect={getAspect(selectedAdv.priority)} size="sm" />
              </div>

              <div className="space-y-3 text-xs">
                <div className="p-3 bg-[#0A0B0D] border border-[#23272F] rounded-sm space-y-1">
                  <span className="text-[10px] text-[#6B7480] uppercase block">Recommended Controller Action</span>
                  <p className="text-sm font-bold text-[#F5A524] leading-relaxed">
                    {selectedAdv.recommendedAction}
                  </p>
                </div>

                <div className="p-3 bg-[#0A0B0D] border border-[#23272F] rounded-sm space-y-1">
                  <span className="text-[10px] text-[#6B7480] uppercase block">Detailed Operational Rationale</span>
                  <p className="font-sans text-[#A3ABB6] leading-relaxed">
                    {selectedAdv.rationale || selectedAdv.title}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-[#0A0B0D] border border-[#23272F] rounded-sm">
                    <span className="text-[10px] text-[#6B7480] uppercase block">Affected Train</span>
                    <span className="text-xs font-bold text-[#E9EBEE] mt-0.5 block">{selectedAdv.trainNo}</span>
                  </div>

                  <div className="p-3 bg-[#0A0B0D] border border-[#23272F] rounded-sm">
                    <span className="text-[10px] text-[#6B7480] uppercase block">Runtime Impact</span>
                    <span className="text-xs font-bold text-[#3DDC97] mt-0.5 block">
                      ▼ {selectedAdv.simulatedImpact?.delaySavingsMinutes || 12}m Net Recovery
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Buttons for Pending Advisories */}
              {selectedAdv.status === 'pending' ? (
                <div className="flex items-center gap-3 pt-4 border-t border-[#23272F]">
                  <button
                    type="button"
                    onClick={() => openActionModal('accept', selectedAdv.id)}
                    className="flex-1 py-2.5 bg-[#F5A524] hover:bg-[#F5A524]/90 text-[#0A0B0D] font-bold text-xs rounded-sm transition-colors flex items-center justify-center gap-2 shadow-sm"
                  >
                    <Check className="w-4 h-4" />
                    <span>Accept Advisory [A]</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => openActionModal('dismiss', selectedAdv.id)}
                    className="px-4 py-2.5 bg-[#0A0B0D] hover:bg-[#15181D] border border-[#23272F] hover:border-[#F4506A] text-[#A3ABB6] hover:text-[#F4506A] font-semibold text-xs rounded-sm transition-colors flex items-center gap-1.5"
                  >
                    <X className="w-4 h-4" />
                    <span>Dismiss [D]</span>
                  </button>
                </div>
              ) : (
                <div className="p-3 bg-[#0A0B0D] border border-[#23272F] rounded-sm text-xs text-[#3DDC97] flex items-center gap-2 font-bold">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Advisory Status: {selectedAdv.status.toUpperCase()}</span>
                </div>
              )}

              <Provenance source="FASTAPI ADVISORY INFERENCE ENGINE" />
            </div>
          ) : (
            <div className="p-8 bg-[#101216] border border-[#23272F] rounded-lg text-center text-xs text-[#6B7480]">
              Select an advisory from the list to inspect details.
            </div>
          )}
        </div>
      </div>

      {/* Confirmation Reason Modal */}
      {reasonModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[#101216] border border-[#23272F] rounded-lg p-6 space-y-4 shadow-2xl">
            <h3 className="text-sm font-bold text-[#E9EBEE] uppercase tracking-wider">
              {modalAction === 'accept' ? 'Sign-Off Advisory' : 'Dismiss Advisory'}
            </h3>

            <p className="text-xs font-sans text-[#A3ABB6]">
              Provide an operational rationale. This action will be cryptographically signed in the audit log.
            </p>

            <textarea
              rows={3}
              value={customReason}
              onChange={e => setCustomReason(e.target.value)}
              className="w-full bg-[#0A0B0D] border border-[#23272F] focus:border-[#F5A524] rounded-sm p-2.5 text-xs text-[#E9EBEE]"
            />

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setReasonModalOpen(false)}
                className="px-3.5 py-1.5 bg-[#0A0B0D] border border-[#23272F] text-xs text-[#A3ABB6] hover:text-[#E9EBEE] rounded-sm"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={handleConfirmAction}
                className={`px-4 py-1.5 text-xs font-bold rounded-sm ${
                  modalAction === 'accept'
                    ? 'bg-[#F5A524] text-[#0A0B0D]'
                    : 'bg-[#F4506A] text-[#0A0B0D]'
                }`}
              >
                Confirm Sign-Off
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
