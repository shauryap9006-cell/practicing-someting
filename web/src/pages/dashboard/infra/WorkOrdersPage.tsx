import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { Kanban, Plus, CheckCircle, Clock, ShieldCheck, ArrowRight, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';

interface WorkOrder {
  id: string;
  title: string;
  linked_asset: string;
  column: 'OPEN' | 'ASSIGNED' | 'IN_PROGRESS' | 'VERIFIED';
  priority: 'critical' | 'high' | 'medium' | 'low';
  due_date: string;
  assignee: string;
  permit_no?: string | null;
}

const COLUMNS = [
  { id: 'OPEN', label: '1. Open Requests' },
  { id: 'ASSIGNED', label: '2. Assigned Gang' },
  { id: 'IN_PROGRESS', label: '3. In Progress (Possession)' },
  { id: 'VERIFIED', label: '4. Verified & Closed' },
] as const;

export function WorkOrdersPage() {
  const [orders, setOrders] = useState<WorkOrder[]>([]);

  useEffect(() => {
    api.getWorkOrders().then(data => setOrders(data as WorkOrder[]));
  }, []);

  const moveOrder = async (id: string, targetCol: WorkOrder['column']) => {
    const prevOrders = [...orders];
    setOrders(prev =>
      prev.map(o => (o.id === id ? { ...o, column: targetCol } : o))
    );

    try {
      await api.updateWorkOrderStatus(id, targetCol);
      toast.success(`Work Order ${id} moved to ${targetCol}.`, {
        action: {
          label: 'Undo (5s)',
          onClick: () => {
            setOrders(prevOrders);
            api.updateWorkOrderStatus(id, prevOrders.find(o => o.id === id)?.column || 'OPEN');
          },
        },
      });
    } catch {
      setOrders(prevOrders);
      toast.error('Failed to update work order column.');
    }
  };

  return (
    <div className="space-y-4 font-mono text-xs">
      <SEO title="Maintenance Work Orders Kanban · RailTwin-X" noindex />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <Kanban className="w-4 h-4 text-[#FFB224]" />
            <span>Maintenance Work Orders Kanban Board</span>
          </h1>
          <p className="text-[#9A9DA3]">
            Track maintenance tasks linked directly to track possession permits and asset registries
          </p>
        </div>

        <button
          onClick={() => toast.info('New Work Order creation dialog.')}
          className="px-3 py-1.5 bg-[#FFB224] hover:bg-[#E59F1C] text-[#0E0F11] font-bold text-xs flex items-center gap-1.5 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Create Work Order</span>
        </button>
      </div>

      {/* Kanban Board 4 Columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {COLUMNS.map(col => {
          const columnOrders = orders.filter(o => o.column === col.id);
          return (
            <div key={col.id} className="bg-[#15171A] border border-[#26282C] flex flex-col">
              {/* Column Header */}
              <div className="bg-[#1B1D21] border-b border-[#26282C] p-3 flex items-center justify-between">
                <span className="font-bold text-xs text-[#E8E8E6] uppercase">{col.label}</span>
                <span className="bg-[#0E0F11] border border-[#26282C] text-[#FFB224] px-2 py-0.5 text-[10px] font-bold">
                  {columnOrders.length}
                </span>
              </div>

              {/* Column Cards Container */}
              <div className="p-3 space-y-3 flex-1 min-h-[420px]">
                {columnOrders.map(order => {
                  const priorityBorder =
                    order.priority === 'critical'
                      ? 'border-l-4 border-l-[#F0533A]'
                      : order.priority === 'high'
                      ? 'border-l-4 border-l-[#FFB224]'
                      : 'border-l-4 border-l-[#3ECF8E]';

                  return (
                    <div
                      key={order.id}
                      className={`bg-[#0E0F11] border border-[#26282C] p-3 space-y-2 ${priorityBorder} hover:border-[#9A9DA3] transition-colors`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="font-bold text-[#FFB224] text-[11px]">{order.id}</span>
                        <span className="text-[10px] text-[#9A9DA3]">{order.due_date}</span>
                      </div>

                      <div className="text-xs font-semibold text-[#E8E8E6] font-sans leading-tight">
                        {order.title}
                      </div>

                      <div className="bg-[#15171A] p-2 border border-[#26282C] text-[11px] text-[#9A9DA3] space-y-1">
                        <div>Asset: <span className="text-[#E8E8E6]">{order.linked_asset}</span></div>
                        <div>Assignee: <span className="text-[#E8E8E6]">{order.assignee}</span></div>
                        {order.permit_no && (
                          <div className="text-[#3ECF8E] font-bold">Permit: {order.permit_no}</div>
                        )}
                      </div>

                      {/* Quick Move Buttons */}
                      <div className="pt-2 border-t border-[#1B1D21] flex justify-between items-center text-[10px]">
                        {col.id !== 'OPEN' && (
                          <button
                            onClick={() => {
                              const colIdx = COLUMNS.findIndex(c => c.id === col.id);
                              if (colIdx > 0) moveOrder(order.id, COLUMNS[colIdx - 1].id as WorkOrder['column']);
                            }}
                            className="text-[#9A9DA3] hover:text-[#E8E8E6] flex items-center gap-1"
                          >
                            <ArrowLeft className="w-3 h-3" />
                            <span>Prev</span>
                          </button>
                        )}

                        {col.id !== 'VERIFIED' && (
                          <button
                            onClick={() => {
                              const colIdx = COLUMNS.findIndex(c => c.id === col.id);
                              if (colIdx < COLUMNS.length - 1) moveOrder(order.id, COLUMNS[colIdx + 1].id as WorkOrder['column']);
                            }}
                            className="text-[#FFB224] hover:underline ml-auto flex items-center gap-1"
                          >
                            <span>Advance</span>
                            <ArrowRight className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}

                {columnOrders.length === 0 && (
                  <div className="text-[#6B6E74] text-center py-10">No work orders in this phase.</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
