import React, { useState } from 'react';

export interface ReceiptChipProps {
  hash?: string | null;
  timestamp?: string;
  blockNumber?: number;
  status?: 'SEALED' | 'PENDING';
  trainNo?: string;
  className?: string;
}

export const ReceiptChip: React.FC<ReceiptChipProps> = ({
  hash,
  timestamp,
  blockNumber,
  status = hash ? 'SEALED' : 'PENDING',
  trainNo,
  className = '',
}) => {
  const [copied, setCopied] = useState(false);

  const isSealed = status === 'SEALED' && Boolean(hash);
  const displayHash = hash
    ? `${hash.slice(0, 8)}...${hash.slice(-6)}`
    : 'PENDING — seals at touchdown';

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (hash) {
      navigator.clipboard.writeText(hash);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div
      className={`inline-flex items-center gap-2 px-2.5 py-1.5 bg-surface border border-line rounded-[4px] font-mono text-xs transition-colors ${className}`}
    >
      <span
        className={`w-2 h-2 rounded-[2px] ${
          isSealed ? 'bg-clear' : 'bg-ochre animate-pulse'
        }`}
      />
      <div className="flex items-center gap-1.5">
        <span className="text-muted text-[10px] uppercase tracking-wider">
          {isSealed ? `BLOCK #${blockNumber || 'LIVE'}` : 'PROOF'}
        </span>
        <span
          className={`tabular-nums ${
            isSealed ? 'text-ink font-medium' : 'text-muted italic'
          }`}
          title={hash || undefined}
        >
          {displayHash}
        </span>
      </div>

      {isSealed && (
        <div className="flex items-center gap-1 pl-1 border-l border-line/60">
          <button
            type="button"
            onClick={handleCopy}
            className="text-[10px] text-muted hover:text-ink hover:underline cursor-pointer select-none"
            title="Copy full cryptographic SHA-256 hash"
          >
            {copied ? 'COPIED' : 'COPY'}
          </button>
          <a
            href={`/proof${hash ? `?hash=${encodeURIComponent(hash)}` : ''}`}
            className="text-[10px] text-ochre hover:underline select-none"
          >
            AUDIT ↗
          </a>
        </div>
      )}
    </div>
  );
};
