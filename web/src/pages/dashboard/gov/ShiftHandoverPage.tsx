import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { BookOpen, CheckSquare, Square, ShieldCheck, Key, FileCheck, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';

interface HandoverData {
  shift: string;
  outgoing_sm: string;
  station_code: string;
  open_incidents_count: number;
  active_tsr_count: number;
  active_blocks_count: number;
  crew_exceptions_count: number;
  status: string;
  checklist: Array<{ item: string; checked: boolean }>;
}

export function ShiftHandoverPage() {
  const [data, setData] = useState<HandoverData | null>(null);
  const [checklist, setChecklist] = useState<Array<{ item: string; checked: boolean }>>([]);
  const [outgoingSignature, setOutgoingSignature] = useState('Rajesh Kumar');
  const [incomingName, setIncomingName] = useState('Amitabh Sharma');
  const [remarks, setRemarks] = useState('All platforms clear. Caution order active at KM 1014.');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [signatureHash, setSignatureHash] = useState<string | null>(null);

  useEffect(() => {
    api.getCurrentHandover().then(res => {
      setData(res as HandoverData);
      setChecklist((res as HandoverData).checklist || []);
    });
  }, []);

  const toggleCheck = (idx: number) => {
    setChecklist(prev => {
      const next = [...prev];
      next[idx] = { ...next[idx], checked: !next[idx].checked };
      return next;
    });
  };

  const handleSubmitHandover = async (e: React.FormEvent) => {
    e.preventDefault();
    const allChecked = checklist.every(c => c.checked);
    if (!allChecked) {
      toast.error('All mandatory statutory checklist items must be verified before shift sign-off.');
      return;
    }

    try {
      const res = await api.submitHandover({
        outgoing_sm: outgoingSignature,
        incoming_sm: incomingName,
        remarks,
        checklist,
      });

      setIsSubmitted(true);
      setSignatureHash((res as { signature_hash: string }).signature_hash);
      toast.success('Shift handover digitally signed and recorded in permanent logbook.');
    } catch {
      toast.error('Failed to submit shift handover.');
    }
  };

  return (
    <div className="space-y-4 font-mono text-xs">
      <SEO title="Digital Shift Handover Logbook · RailTwin-X" noindex />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-[#FFB224]" />
            <span>Digital Shift Handover Logbook</span>
          </h1>
          <p className="text-[#9A9DA3]">
            Statutory 8-Hour Station Master Shift Exchange (08:00 / 16:00 / 00:00)
          </p>
        </div>

        <div className="text-right">
          <span className="text-[10px] text-[#9A9DA3] block">CURRENT SHIFT</span>
          <span className="text-[#FFB224] font-bold text-xs">16:00 – 00:00 (Evening Shift)</span>
        </div>
      </div>

      {/* Handover Form & Summary Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Aggregated Shift Status & Checklist */}
        <div className="lg:col-span-7 bg-[#15171A] border border-[#26282C] p-5 space-y-4">
          <div className="font-bold text-sm text-[#E8E8E6] border-b border-[#26282C] pb-2">
            1. Automated Shift Telemetry Snapshot
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div className="bg-[#0E0F11] p-3 border border-[#26282C]">
              <span className="text-[10px] text-[#9A9DA3] block">OPEN INCIDENTS</span>
              <span className="font-bold text-sm text-[#F0533A]">1 Active</span>
            </div>
            <div className="bg-[#0E0F11] p-3 border border-[#26282C]">
              <span className="text-[10px] text-[#9A9DA3] block">ACTIVE TSRs</span>
              <span className="font-bold text-sm text-[#FFB224]">2 Caution</span>
            </div>
            <div className="bg-[#0E0F11] p-3 border border-[#26282C]">
              <span className="text-[10px] text-[#9A9DA3] block">TRACK BLOCKS</span>
              <span className="font-bold text-sm text-[#3ECF8E]">2 Granted</span>
            </div>
            <div className="bg-[#0E0F11] p-3 border border-[#26282C]">
              <span className="text-[10px] text-[#9A9DA3] block">CREW WARNINGS</span>
              <span className="font-bold text-sm text-[#FFB224]">1 Near Breach</span>
            </div>
          </div>

          <div className="space-y-3 pt-2">
            <div className="font-bold text-xs text-[#E8E8E6]">2. Mandatory Safety Handover Checklist</div>
            {checklist.map((c, idx) => (
              <div
                key={idx}
                onClick={() => toggleCheck(idx)}
                className={`p-3 border flex items-center gap-3 cursor-pointer transition-colors ${
                  c.checked ? 'bg-[#0E0F11] border-[#3ECF8E]/40 text-[#E8E8E6]' : 'bg-[#0E0F11] border-[#26282C] text-[#9A9DA3]'
                }`}
              >
                {c.checked ? (
                  <CheckSquare className="w-4 h-4 text-[#3ECF8E]" />
                ) : (
                  <Square className="w-4 h-4 text-[#9A9DA3]" />
                )}
                <span className="text-xs font-sans">{c.item}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Digital Signature & Seal */}
        <div className="lg:col-span-5 bg-[#15171A] border border-[#26282C] p-5 space-y-4">
          <div className="font-bold text-sm text-[#E8E8E6] border-b border-[#26282C] pb-2">
            3. Digital Handover Signatures
          </div>

          <form onSubmit={handleSubmitHandover} className="space-y-3">
            <div>
              <label className="text-[10px] text-[#9A9DA3] block mb-1">Outgoing Station Master</label>
              <input
                type="text"
                value={outgoingSignature}
                onChange={e => setOutgoingSignature(e.target.value)}
                className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
              />
            </div>

            <div>
              <label className="text-[10px] text-[#9A9DA3] block mb-1">Incoming Station Master</label>
              <input
                type="text"
                value={incomingName}
                onChange={e => setIncomingName(e.target.value)}
                className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
              />
            </div>

            <div>
              <label className="text-[10px] text-[#9A9DA3] block mb-1">Shift Handover Remarks</label>
              <textarea
                rows={3}
                value={remarks}
                onChange={e => setRemarks(e.target.value)}
                className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
              />
            </div>

            {isSubmitted ? (
              <div className="bg-[#3ECF8E]/10 border border-[#3ECF8E] p-4 text-center space-y-2">
                <FileCheck className="w-8 h-8 text-[#3ECF8E] mx-auto" />
                <div className="font-bold text-[#3ECF8E] text-xs">SHIFT HANDOVER SEALED</div>
                <div className="text-[10px] text-[#9A9DA3]">Hash: {signatureHash}</div>
              </div>
            ) : (
              <button
                type="submit"
                className="w-full py-2.5 bg-[#FFB224] hover:bg-[#E59F1C] text-[#0E0F11] font-bold text-xs flex items-center justify-center gap-2 transition-colors"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>Digitally Sign & Hand Over Shift</span>
              </button>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}
