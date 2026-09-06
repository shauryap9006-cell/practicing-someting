import React, { useState } from 'react';
import { CheckCircle2, ShieldCheck, RefreshCw } from 'lucide-react';

interface ChainBlock {
  index: number;
  hash: string;
  prevHash: string;
  action: string;
  actor: string;
  timestamp: string;
  verified: boolean;
}

const INITIAL_BLOCKS: ChainBlock[] = [
  {
    index: 104,
    hash: '0x8f2a11b9c402e9a781b0',
    prevHash: '0x3d91ea4489b01c379a2f',
    action: 'ADVISORY_ACCEPTED (Adv-2026-081)',
    actor: 'SM-CNB (Rajesh Kumar)',
    timestamp: '17:42:15 IST',
    verified: true,
  },
  {
    index: 103,
    hash: '0x3d91ea4489b01c379a2f',
    prevHash: '0x7e44a108b9c2049102bc',
    action: 'PLATFORM_REALLOCATED (12034 -> PF3)',
    actor: 'MILP_SOLVER (Auto-pass)',
    timestamp: '17:39:00 IST',
    verified: true,
  },
  {
    index: 102,
    hash: '0x7e44a108b9c2049102bc',
    prevHash: '0x1a998c4402eb991048ca',
    action: 'TSR_ISSUED (CO-NCR-CNB-1014)',
    actor: 'CTRL-CAWNPORE (Vikram Seth)',
    timestamp: '17:30:22 IST',
    verified: true,
  },
  {
    index: 101,
    hash: '0x1a998c4402eb991048ca',
    prevHash: '0x99104fa288bc0192ea01',
    action: 'CREW_RELIEF_DISPATCHED (LP-CNB-04)',
    actor: 'CREW_CTRL (Suresh Raina)',
    timestamp: '17:15:08 IST',
    verified: true,
  },
];

export function AuditChainVisual() {
  const [blocks, setBlocks] = useState<ChainBlock[]>(INITIAL_BLOCKS);
  const [isVerifying, setIsVerifying] = useState(false);

  const handleReverify = () => {
    setIsVerifying(true);
    setBlocks(prev => prev.map(b => ({ ...b, verified: false })));

    blocks.forEach((_, idx) => {
      setTimeout(() => {
        setBlocks(prev => {
          const next = [...prev];
          next[idx] = { ...next[idx], verified: true };
          return next;
        });
        if (idx === blocks.length - 1) {
          setIsVerifying(false);
        }
      }, (idx + 1) * 250);
    });
  };

  return (
    <div className="bg-[#15171A] border border-[#26282C] p-6 sm:p-8 font-mono text-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-6 border-b border-[#26282C] gap-4">
        <div className="flex items-center gap-3">
          <ShieldCheck className="w-5 h-5 text-[#3ECF8E]" />
          <div>
            <div className="text-sm font-semibold text-[#E8E8E6]">Cryptographic Audit Ledger Chain</div>
            <div className="text-[11px] text-[#9A9DA3]">SHA-256 HMAC Linked · Tamper-Evident State</div>
          </div>
        </div>

        <button
          onClick={handleReverify}
          disabled={isVerifying}
          className="flex items-center gap-2 px-3 py-1.5 bg-[#1B1D21] border border-[#26282C] text-[#FFB224] hover:bg-[#FFB224] hover:text-[#0E0F11] transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isVerifying ? 'animate-spin' : ''}`} />
          <span>{isVerifying ? 'Verifying Hashes...' : 'Re-verify Chain'}</span>
        </button>
      </div>

      {/* Blocks sequence */}
      <div className="space-y-4 relative">
        {/* Connecting vertical line */}
        <div className="absolute left-[17px] top-4 bottom-4 w-0.5 bg-[#26282C] -z-0" />

        {blocks.map(block => (
          <div
            key={block.index}
            className={`relative z-10 bg-[#0E0F11] border p-4 transition-all duration-300 ${
              block.verified ? 'border-[#3ECF8E]/40' : 'border-[#26282C]'
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div
                  className={`w-6 h-6 flex items-center justify-center border transition-colors ${
                    block.verified
                      ? 'bg-[#3ECF8E]/10 border-[#3ECF8E] text-[#3ECF8E]'
                      : 'bg-[#15171A] border-[#26282C] text-[#9A9DA3]'
                  }`}
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                </div>
                <div>
                  <div className="text-[#E8E8E6] font-semibold flex items-center gap-2">
                    <span>Block #{block.index}</span>
                    <span className="text-[#FFB224] text-[11px]">{block.action}</span>
                  </div>
                  <div className="text-[#9A9DA3] text-[11px] mt-0.5">Actor: {block.actor}</div>
                </div>
              </div>

              <div className="text-right">
                <span className="text-[#9A9DA3] text-[11px]">{block.timestamp}</span>
                <div className="text-[10px] text-[#3ECF8E] font-mono mt-0.5">
                  {block.verified ? 'SEALED & INTACT' : 'PENDING CHECK'}
                </div>
              </div>
            </div>

            <div className="mt-3 pt-2 border-t border-[#1B1D21] flex flex-col sm:flex-row sm:items-center justify-between text-[10px] text-[#9A9DA3] gap-1">
              <div>Current Hash: <span className="text-[#E8E8E6]">{block.hash}</span></div>
              <div>Prev Hash: <span className="text-[#9A9DA3]">{block.prevHash}</span></div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 pt-3 border-t border-[#26282C] text-[11px] text-[#9A9DA3] flex items-center justify-between">
        <span>Continuous Mathematical Verification</span>
        <span className="text-[#3ECF8E] font-semibold">100% Chain Integrity Verified</span>
      </div>
    </div>
  );
}
