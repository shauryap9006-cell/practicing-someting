import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Advisory } from '@/mock/types';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { DataFreshnessBadge } from '@/components/common/DataFreshnessBadge';
import { AlertTriangle, Check, X, ShieldAlert, Clock, Sparkles, Filter } from 'lucide-react';
import { toast } from 'sonner';

export const AdvisoriesPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: advisories = [], dataUpdatedAt } = useQuery({
    queryKey: queryKeys.advisories(),
    queryFn: () => api.getAdvisories(),
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
    },
  });

  const dismissMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => api.dismissAdvisory(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.advisories() });
      toast.info('Advisory Dismissed', {
        description: 'Retained current dispatch plan under dispatcher discretion.',
      });
    },
  });

  const filteredAdvisories = advisories.filter(a => {
    if (statusFilter === 'all') return true;
    return a.status === statusFilter;
  });

  // Set default selected advisory
  useEffect(() => {
    if (filteredAdvisories.length > 0 && !selectedAdvId) {
      setSelectedAdvId(filteredAdvisories[0].id);
    }
  }, [filteredAdvisories, selectedAdvId]);

  // Keyboard navigation: A = Accept, D = Dismiss per §9
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
        ? 'Accepted per recommendation; route signal indicators cleared.'
        : 'Dispatcher discretion override: retained existing section plan.'
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
    setReasonModalOpen(false);
  };

  const selectedAdvisory = advisories.find(a => a.id === selectedAdvId);

  return (
    <div className="space-y-4 font-sans">
      {/* Header & Hotkey Bar */}
      <div className="bg-panel border border-hairline p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold font-mono text-text-main flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-accent stroke-[1.5]" />
            <span>DISPATCH ADVISORY TRIAGE QUEUE</span>
          </h2>
          <p className="text-xs text-text-dim mt-0.5">
            Decisions are advisory only. Every recommendation requires human sign-off and is logged for regulatory audit.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <DataFreshnessBadge dataUpdatedAt={dataUpdatedAt} />
          {/* Hotkey Hint */}
          <div className="flex items-center gap-2 text-xs font-mono text-text-dim bg-panel-2 border border-hairline px-3 py-1.5 rounded-none">
            <span>Hotkeys:</span>
          <kbd className="px-1.5 py-0.5 bg-panel border border-hairline text-text-main font-bold">A</kbd>
          <span>Accept</span>
          <kbd className="px-1.5 py-0.5 bg-panel border border-hairline text-text-main font-bold">D</kbd>
          <span>Dismiss</span>
        </div>
      </div>
    </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-hairline pb-2 text-xs font-mono">
        <button
          onClick={() => setStatusFilter('pending')}
          className={`px-3 py-1 border transition-colors ${
            statusFilter === 'pending'
              ? 'bg-panel-2 border-accent text-accent font-bold'
              : 'border-hairline text-text-dim hover:text-text-main'
          }`}
        >
          Pending ({advisories.filter(a => a.status === 'pending').length})
        </button>
        <button
          onClick={() => setStatusFilter('accepted')}
          className={`px-3 py-1 border transition-colors ${
            statusFilter === 'accepted'
              ? 'bg-panel-2 border-accent text-accent font-bold'
              : 'border-hairline text-text-dim hover:text-text-main'
          }`}
        >
          Accepted ({advisories.filter(a => a.status === 'accepted').length})
        </button>
        <button
          onClick={() => setStatusFilter('dismissed')}
          className={`px-3 py-1 border transition-colors ${
            statusFilter === 'dismissed'
              ? 'bg-panel-2 border-accent text-accent font-bold'
              : 'border-hairline text-text-dim hover:text-text-main'
          }`}
        >
          Dismissed ({advisories.filter(a => a.status === 'dismissed').length})
        </button>
        <button
          onClick={() => setStatusFilter('all')}
          className={`px-3 py-1 border transition-colors ${
            statusFilter === 'all'
              ? 'bg-panel-2 border-accent text-accent font-bold'
              : 'border-hairline text-text-dim hover:text-text-main'
          }`}
        >
          All ({advisories.length})
        </button>
      </div>

      {/* Two Column Triage Layout: Queue List (Left) + Detail & Sign-Off (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Advisory Queue */}
        <div className="lg:col-span-5 space-y-2">
          {filteredAdvisories.length === 0 ? (
            <div className="p-12 text-center bg-panel border border-hairline text-xs font-mono text-text-dim space-y-2">
              <ShieldAlert className="w-8 h-8 mx-auto text-ok stroke-[1.5]" />
              <div className="font-bold text-text-main">No advisories. Corridor nominal.</div>
              <div>All sections and platform slots running under nominal safety parameters.</div>
            </div>
          ) : (
            filteredAdvisories.map(adv => {
              const isSelected = adv.id === selectedAdvId;
              return (
                <div
                  key={adv.id}
                  onClick={() => setSelectedAdvId(adv.id)}
                  className={`p-3.5 bg-panel border cursor-pointer transition-all text-xs space-y-2 ${
                    isSelected
                      ? 'border-accent bg-panel-2'
                      : 'border-hairline hover:border-text-dim/60'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 font-mono">
                    <span className="font-bold text-text-main">{adv.code} · Train {adv.trainNo}</span>
                    <Badge variant={adv.priority === 'danger' ? 'danger' : adv.priority === 'warn' ? 'warn' : 'neutral'}>
                      {adv.status === 'pending' ? adv.priority.toUpperCase() : adv.status.toUpperCase()}
                    </Badge>
                  </div>

                  <div className="font-semibold text-text-main font-sans text-xs line-clamp-1">
                    {adv.title}
                  </div>

                  <p className="text-[11px] text-text-dim font-sans line-clamp-2 leading-relaxed">
                    {adv.rationale}
                  </p>

                  <div className="pt-1.5 border-t border-hairline/60 flex items-center justify-between text-[10px] font-mono text-text-dim">
                    <span>Impact: +{adv.simulatedImpact.delaySavingsMinutes}m savings</span>
                    <span>Created: {adv.createdAt}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Column: Selected Advisory Full Detail & Dispatcher Action */}
        <div className="lg:col-span-7">
          {selectedAdvisory ? (
            <div className="bg-panel border border-hairline p-5 space-y-5">
              <div className="flex items-start justify-between border-b border-hairline pb-3">
                <div>
                  <div className="flex items-center gap-2 font-mono text-xs text-text-dim">
                    <span className="font-bold text-accent">{selectedAdvisory.code}</span>
                    <span>•</span>
                    <span>Train {selectedAdvisory.trainNo} {selectedAdvisory.trainName}</span>
                  </div>
                  <h3 className="text-base font-bold text-text-main font-sans mt-1">
                    {selectedAdvisory.title}
                  </h3>
                </div>
                <Badge variant={selectedAdvisory.priority === 'danger' ? 'danger' : selectedAdvisory.priority === 'warn' ? 'warn' : 'neutral'}>
                  {selectedAdvisory.status.toUpperCase()}
                </Badge>
              </div>

              {/* Rationale & Operational Context */}
              <div className="space-y-2">
                <div className="text-[11px] font-mono uppercase tracking-wider text-text-dim">
                  Detection Rationale & Evidence
                </div>
                <div className="p-3 bg-panel-2 border border-hairline text-xs font-sans text-text-main leading-relaxed">
                  {selectedAdvisory.rationale}
                </div>
              </div>

              {/* Recommended Action */}
              <div className="space-y-2">
                <div className="text-[11px] font-mono uppercase tracking-wider text-text-dim">
                  Recommended Dispatcher Action
                </div>
                <div className="p-3 bg-panel-2 border border-accent/40 text-xs font-mono text-accent leading-relaxed font-semibold">
                  {selectedAdvisory.recommendedAction}
                </div>
              </div>

              {/* Simulated Network Impact Breakdown */}
              <div className="space-y-2">
                <div className="text-[11px] font-mono uppercase tracking-wider text-text-dim">
                  Simulated Network Impact
                </div>
                <div className="grid grid-cols-3 gap-3 text-center font-mono text-xs">
                  <div className="p-2.5 bg-panel-2 border border-hairline">
                    <div className="text-[10px] text-text-dim">Delay Savings</div>
                    <div className="text-base font-bold text-ok mt-0.5">
                      +{selectedAdvisory.simulatedImpact.delaySavingsMinutes} min
                    </div>
                  </div>
                  <div className="p-2.5 bg-panel-2 border border-hairline">
                    <div className="text-[10px] text-text-dim">Platform Conflict</div>
                    <div className="text-base font-bold text-text-main mt-0.5">
                      {selectedAdvisory.simulatedImpact.conflictResolved ? 'Resolved' : 'N/A'}
                    </div>
                  </div>
                  <div className="p-2.5 bg-panel-2 border border-hairline">
                    <div className="text-[10px] text-text-dim">Cascades Prevented</div>
                    <div className="text-base font-bold text-accent mt-0.5">
                      {selectedAdvisory.simulatedImpact.cascadePreventedCount} trains
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Buttons if Pending */}
              {selectedAdvisory.status === 'pending' ? (
                <div className="pt-4 border-t border-hairline flex items-center justify-end gap-3">
                  <Button
                    variant="outline"
                    size="md"
                    onClick={() => openActionModal('dismiss', selectedAdvisory.id)}
                    className="text-xs font-mono gap-1.5"
                  >
                    <X className="w-3.5 h-3.5 stroke-[2]" />
                    <span>Dismiss (D)</span>
                  </Button>
                  <Button
                    variant="primary"
                    size="md"
                    onClick={() => openActionModal('accept', selectedAdvisory.id)}
                    className="text-xs font-mono font-semibold gap-1.5"
                  >
                    <Check className="w-3.5 h-3.5 stroke-[2]" />
                    <span>Accept Recommendation (A)</span>
                  </Button>
                </div>
              ) : (
                <div className="pt-3 border-t border-hairline text-xs font-mono text-text-dim flex items-center justify-between">
                  <span>Sign-off record: {selectedAdvisory.triageReason}</span>
                  <span className="text-ok uppercase font-bold">{selectedAdvisory.status}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 bg-panel border border-hairline text-center text-xs text-text-dim font-mono">
              Select an advisory from the queue to view rationale and sign-off options.
            </div>
          )}
        </div>
      </div>

      {/* Triage Reason Sign-Off Modal */}
      {reasonModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-panel border border-hairline p-5 space-y-4 animate-in fade-in zoom-in-95 duration-100">
            <h3 className="text-sm font-bold font-mono text-text-main uppercase tracking-tight">
              {modalAction === 'accept' ? 'Confirm Advisory Acceptance' : 'Dismiss Advisory'}
            </h3>

            <div className="space-y-1">
              <label className="block text-[11px] font-mono uppercase text-text-dim">
                Dispatcher Operational Rationale / Reason
              </label>
              <Input
                value={customReason}
                onChange={e => setCustomReason(e.target.value)}
                placeholder="Enter regulatory rationale..."
                className="text-xs"
                autoFocus
              />
            </div>

            <p className="text-[11px] text-text-dim font-sans">
              This action will be committed to the immutable regulatory audit ledger with timestamp and dispatcher ID.
            </p>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-hairline">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setReasonModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                variant={modalAction === 'accept' ? 'primary' : 'secondary'}
                size="sm"
                onClick={handleConfirmAction}
              >
                Confirm & Log Action
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
