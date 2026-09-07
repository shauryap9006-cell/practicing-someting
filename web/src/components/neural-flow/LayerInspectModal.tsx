import React from 'react';
import { X, Code, ShieldCheck, Cpu } from 'lucide-react';

export interface NodeDetail {
  id: string;
  name: string;
  category: 'INGESTION' | 'EMBEDDING' | 'NEURAL_BACKBONE' | 'ATTENTION' | 'ENSEMBLE' | 'CONFORMAL' | 'SAFETY';
  file: string;
  shapeIn: string;
  shapeOut: string;
  formula: string;
  description: string;
  invariant: string;
}

interface LayerInspectModalProps {
  node: NodeDetail | null;
  onClose: () => void;
}

export const LayerInspectModal: React.FC<LayerInspectModalProps> = ({ node, onClose }) => {
  if (!node) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-2xl bg-surface border-2 border-lineStrong rounded-[4px] shadow-2xl overflow-hidden flex flex-col max-h-[90vh] text-ink z-10"
        onClick={(e) => e.stopPropagation()}
        style={{ backgroundColor: '#FDFCF8' }}
      >
        {/* Header */}
        <div className="p-4 bg-raised border-b border-line flex items-center justify-between select-none">
          <div className="flex items-center gap-2.5">
            <span className="p-2 bg-paper rounded border border-line text-ochre">
              <Cpu size={20} />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-paper border border-lineStrong text-ochre uppercase tracking-wider">
                  {node.category}
                </span>
                <span className="text-[11px] font-mono text-ink2 font-semibold">{node.file}</span>
              </div>
              <h3 className="text-base font-serif font-bold text-ink mt-0.5">{node.name}</h3>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded border border-line bg-paper hover:bg-raised text-ink transition-colors cursor-pointer"
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs font-sans bg-surface" style={{ backgroundColor: '#FDFCF8' }}>
          {/* Tensor Dimensions */}
          <div className="grid grid-cols-2 gap-3 p-3.5 bg-paper rounded border border-lineStrong">
            <div>
              <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-ink2 block">Input Shape</span>
              <span className="font-mono text-ink font-bold text-xs mt-1 block">{node.shapeIn}</span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-ink2 block">Output Shape</span>
              <span className="font-mono text-ochre font-bold text-xs mt-1 block">{node.shapeOut}</span>
            </div>
          </div>

          {/* Mathematical Formula */}
          <div>
            <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-ink block mb-1.5">
              Mathematical Formulation
            </span>
            <div className="p-3 bg-paper rounded border border-lineStrong font-mono text-[11px] text-ink overflow-x-auto leading-relaxed font-medium">
              {node.formula}
            </div>
          </div>

          {/* Architectural Description */}
          <div>
            <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-ink block mb-1.5">
              Architectural Role & Function
            </span>
            <p className="text-ink leading-relaxed text-xs p-3 bg-paper/50 rounded border border-line">
              {node.description}
            </p>
          </div>

          {/* Core Invariant */}
          <div className="p-3 bg-ochreWash rounded border border-ochre/40 flex items-start gap-2.5">
            <ShieldCheck size={18} className="text-ochre shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-ochre text-xs block">Scientific Invariant Guaranteed:</span>
              <span className="text-ink text-[11px] mt-0.5 block leading-relaxed">{node.invariant}</span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 bg-raised border-t border-line flex items-center justify-between text-[11px] font-mono text-ink2 select-none">
          <span className="flex items-center gap-1.5 font-medium">
            <Code size={14} className="text-ochre" /> Native PyTorch 2.0+ / LightGBM Execution Path
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-paper border border-lineStrong hover:bg-raised text-ink font-sans font-semibold rounded text-xs transition-colors cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
};
