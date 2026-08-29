import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { Grid, Radio, AlertCircle, ShieldAlert, CheckCircle2 } from 'lucide-react';

interface BlockSection {
  id: string;
  section_name: string;
  state: 'CLEAR' | 'OCCUPIED' | 'BLOCKED' | 'CAUTION';
  speed_limit: number;
  occupant?: string | null;
  time_in_state: string;
}

export function BlockSectionsPage() {
  const [blocks, setBlocks] = useState<BlockSection[]>([]);
  const [selectedBlock, setSelectedBlock] = useState<BlockSection | null>(null);

  useEffect(() => {
    api.getBlockSections().then(data => {
      setBlocks(data as BlockSection[]);
      if (data.length > 0) setSelectedBlock(data[0] as BlockSection);
    });

    const interval = setInterval(() => {
      api.getBlockSections().then(data => setBlocks(data as BlockSection[]));
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-4">
      <SEO title="Block Section Line Clear Board · RailTwin-X" noindex />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <Grid className="w-4 h-4 text-[#FFB224]" />
            <span>Block Section & Line Status Board</span>
          </h1>
          <p className="font-mono text-xs text-[#9A9DA3]">
            Automatic Block Signaling (ABS) & Interlocking Status · Auto-refresh 5s
          </p>
        </div>

        <div className="flex items-center gap-3 font-mono text-xs">
          <span className="flex items-center gap-1.5 text-[#3ECF8E]">
            <span className="w-2.5 h-2.5 bg-[#3ECF8E]" /> CLEAR
          </span>
          <span className="flex items-center gap-1.5 text-[#FFB224]">
            <span className="w-2.5 h-2.5 bg-[#FFB224]" /> OCCUPIED
          </span>
          <span className="flex items-center gap-1.5 text-[#F0533A]">
            <span className="w-2.5 h-2.5 bg-[#F0533A]" /> BLOCKED
          </span>
        </div>
      </div>

      {/* Grid of Block Cells */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Cells Grid */}
        <div className="lg:col-span-8 grid grid-cols-1 sm:grid-cols-2 gap-3">
          {blocks.map(b => {
            const isSelected = selectedBlock?.id === b.id;
            return (
              <div
                key={b.id}
                onClick={() => setSelectedBlock(b)}
                className={`p-4 border font-mono cursor-pointer transition-all duration-200 ${
                  isSelected ? 'border-[#FFB224] bg-[#1B1D21]' : 'border-[#26282C] bg-[#15171A] hover:border-[#9A9DA3]'
                }`}
              >
                <div className="flex items-start justify-between">
                  <span className="text-[11px] text-[#9A9DA3]">{b.id}</span>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 border ${
                      b.state === 'CLEAR'
                        ? 'border-[#3ECF8E] text-[#3ECF8E] bg-[#3ECF8E]/10'
                        : b.state === 'OCCUPIED'
                        ? 'border-[#FFB224] text-[#FFB224] bg-[#FFB224]/10'
                        : b.state === 'BLOCKED'
                        ? 'border-[#F0533A] text-[#F0533A] bg-[#F0533A]/10'
                        : 'border-[#FFB224] text-[#FFB224] bg-[#FFB224]/10'
                    }`}
                  >
                    {b.state}
                  </span>
                </div>

                <div className="text-sm font-semibold text-[#E8E8E6] mt-2 mb-3">
                  {b.section_name}
                </div>

                <div className="flex items-center justify-between text-xs pt-2 border-t border-[#26282C] text-[#9A9DA3]">
                  <span>Occupant: <strong className="text-[#E8E8E6]">{b.occupant || 'None (Line Clear)'}</strong></span>
                  <span>Time: {b.time_in_state}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Block Inspector */}
        <div className="lg:col-span-4 bg-[#15171A] border border-[#26282C] p-5 font-mono text-xs space-y-4">
          <div className="flex items-center justify-between border-b border-[#26282C] pb-2">
            <span className="font-bold text-[#E8E8E6] uppercase text-sm">Block Detail Inspector</span>
            <Radio className="w-4 h-4 text-[#FFB224] animate-pulse" />
          </div>

          {selectedBlock ? (
            <div className="space-y-4">
              <div>
                <span className="text-[10px] text-[#9A9DA3] uppercase block">Section Name</span>
                <span className="font-bold text-sm text-[#E8E8E6]">{selectedBlock.section_name}</span>
              </div>

              <div className="grid grid-cols-2 gap-3 bg-[#0E0F11] p-3 border border-[#26282C]">
                <div>
                  <span className="text-[10px] text-[#9A9DA3] block uppercase">Line State</span>
                  <span className="font-bold text-sm text-[#FFB224]">{selectedBlock.state}</span>
                </div>
                <div>
                  <span className="text-[10px] text-[#9A9DA3] block uppercase">Section Speed Limit</span>
                  <span className="font-bold text-sm text-[#E8E8E6]">{selectedBlock.speed_limit} km/h</span>
                </div>
              </div>

              <div className="bg-[#0E0F11] p-3 border border-[#26282C]">
                <span className="text-[10px] text-[#9A9DA3] block uppercase">Current Train In Section</span>
                <span className="font-bold text-xs text-[#E8E8E6] mt-1 block">
                  {selectedBlock.occupant ? `Train #${selectedBlock.occupant}` : 'Track Vacant (Clear to Grant Line)'}
                </span>
              </div>

              <div className="pt-2 border-t border-[#26282C] space-y-2 text-[11px] text-[#9A9DA3]">
                <div className="flex justify-between">
                  <span>Signaling System:</span>
                  <span className="text-[#E8E8E6]">Automatic Block Signaling (ABS)</span>
                </div>
                <div className="flex justify-between">
                  <span>Axle Counter Health:</span>
                  <span className="text-[#3ECF8E]">Dual Multi-Section (HEALTHY)</span>
                </div>
                <div className="flex justify-between">
                  <span>Block Instrument:</span>
                  <span className="text-[#E8E8E6]">Diido Tokenless Handle Type</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-[#9A9DA3] py-8 text-center">Select a block section to inspect telemetry.</div>
          )}
        </div>
      </div>
    </div>
  );
}
