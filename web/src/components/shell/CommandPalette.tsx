import React, { useState } from 'react';
import { Command } from 'cmdk';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { StationCode } from '@/mock/types';
import {
  Activity,
  Calendar,
  Train,
  Bell,
  Users,
  Wrench,
  Shield,
  FileCode,
  MapPin,
  Search,
  Navigation,
  Layers,
  Clock,
  Grid,
  Truck,
  ShieldAlert,
  AlertCircle,
  FileCheck,
  Store,
  Sparkles,
  Radio,
  BookOpen,
  UserCheck,
  Database,
} from 'lucide-react';

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const navigate = useNavigate();
  const [activeStation, setActiveStation] = useState<StationCode>('CNB');

  const { data: trains = [] } = useQuery({
    queryKey: queryKeys.board(activeStation),
    queryFn: () => api.getTrains(),
    enabled: open,
  });

  const handleSelectRoute = (path: string) => {
    navigate(path);
    onOpenChange(false);
  };

  const handleSelectStation = async (code: StationCode) => {
    setActiveStation(code);
    try {
      await api.switchStation(code, 'CMD_PALETTE');
    } catch {
      // ignore
    }
    onOpenChange(false);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center pt-20 p-4 font-mono select-none">
      <div
        className="w-full max-w-xl bg-[#101216] border border-[#23272F] shadow-2xl rounded-lg overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <Command
          className="w-full bg-transparent text-[#E9EBEE] text-xs"
          loop
        >
          <div className="flex items-center gap-2 px-3 py-3 border-b border-[#23272F] bg-[#0A0B0D]">
            <Search className="w-4 h-4 text-[#A3ABB6]" />
            <Command.Input
              autoFocus
              placeholder="Type train no (#12301), station (CNB), or module..."
              className="w-full bg-transparent text-[#E9EBEE] placeholder-[#6B7480] text-xs focus:outline-none"
            />
            <kbd className="text-[10px] text-[#6B7480] border border-[#23272F] px-1.5 py-0.5 rounded-xs">ESC</kbd>
          </div>

          <Command.List className="max-h-80 overflow-y-auto p-2 space-y-1">
            <Command.Empty className="py-6 text-center text-[#A3ABB6] text-xs">
              No matching modules, actions, or trains found.
            </Command.Empty>

            {/* Quick Actions */}
            <Command.Group heading="Operational Shortcuts" className="text-[10px] uppercase text-[#6B7480] px-2 py-1 font-bold">
              <Command.Item
                onSelect={() => handleSelectRoute('/dashboard/gantt')}
                className="flex items-center gap-2 px-2.5 py-2 rounded-sm cursor-pointer text-[#E9EBEE] hover:bg-[#15181D] hover:text-[#F5A524] transition-colors"
              >
                <Sparkles className="w-4 h-4 text-[#F5A524]" />
                <span>Platform Gantt Re-Optimizer (MILP)</span>
              </Command.Item>
              <Command.Item
                onSelect={() => handleSelectRoute('/dashboard/live-map')}
                className="flex items-center gap-2 px-2.5 py-2 rounded-sm cursor-pointer text-[#E9EBEE] hover:bg-[#15181D] hover:text-[#F5A524] transition-colors"
              >
                <Navigation className="w-4 h-4 text-[#3DDC97]" />
                <span>Line Radar Telemetry (Subway View)</span>
              </Command.Item>
              <Command.Item
                onSelect={() => handleSelectRoute('/dashboard/safety/tsr')}
                className="flex items-center gap-2 px-2.5 py-2 rounded-sm cursor-pointer text-[#E9EBEE] hover:bg-[#15181D] hover:text-[#F5A524] transition-colors"
              >
                <ShieldAlert className="w-4 h-4 text-[#F4506A]" />
                <span>Issue Caution Order / Speed Restriction</span>
              </Command.Item>
            </Command.Group>

            {/* Navigation Modules */}
            <Command.Group heading="Station Modules" className="text-[10px] uppercase text-[#6B6E74] px-2 py-1 font-bold">
              <Command.Item
                onSelect={() => handleSelectRoute('/dashboard')}
                className="flex items-center gap-2 px-2.5 py-2 rounded-sm cursor-pointer text-[#E9EBEE] hover:bg-[#15181D] hover:text-[#F5A524] transition-colors"
              >
                <Activity className="w-4 h-4" />
                <span>Duty Board Control Room Overview</span>
              </Command.Item>
              <Command.Item
                onSelect={() => handleSelectRoute('/dashboard/trains')}
                className="flex items-center gap-2 px-2.5 py-2 rounded-sm cursor-pointer text-[#E9EBEE] hover:bg-[#15181D] hover:text-[#F5A524] transition-colors"
              >
                <Train className="w-4 h-4" />
                <span>Trains Directory & Delay Autopsy</span>
              </Command.Item>
              <Command.Item
                onSelect={() => handleSelectRoute('/dashboard/advisories')}
                className="flex items-center gap-2 px-2.5 py-2 rounded-sm cursor-pointer text-[#E9EBEE] hover:bg-[#15181D] hover:text-[#F5A524] transition-colors"
              >
                <Bell className="w-4 h-4" />
                <span>Advisory Triage Queue</span>
              </Command.Item>
              <Command.Item
                onSelect={() => handleSelectRoute('/dashboard/crew')}
                className="flex items-center gap-2 px-2.5 py-2 rounded-sm cursor-pointer text-[#E9EBEE] hover:bg-[#15181D] hover:text-[#F5A524] transition-colors"
              >
                <Users className="w-4 h-4" />
                <span>Crew Rosters & 10h Duty Limits</span>
              </Command.Item>
              <Command.Item
                onSelect={() => handleSelectRoute('/kiosk')}
                className="flex items-center gap-2 px-2.5 py-2 rounded-sm cursor-pointer text-[#E9EBEE] hover:bg-[#15181D] hover:text-[#F5A524] transition-colors"
              >
                <Store className="w-4 h-4 text-[#3DDC97]" />
                <span>Passenger Kiosk PIDS Screen</span>
              </Command.Item>
            </Command.Group>

            {/* Stations Switcher */}
            <Command.Group heading="Switch Station Yard" className="text-[10px] uppercase text-[#6B7480] px-2 py-1 font-bold">
              {(['CNB', 'NDLS', 'GZB'] as StationCode[]).map(code => (
                <Command.Item
                  key={code}
                  onSelect={() => handleSelectStation(code)}
                  className="flex items-center justify-between px-2.5 py-2 rounded-sm cursor-pointer text-[#E9EBEE] hover:bg-[#15181D] hover:text-[#F5A524] transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <MapPin className="w-3.5 h-3.5" />
                    <span>{code} Station Yard</span>
                  </div>
                  {activeStation === code && (
                    <span className="text-[10px] text-[#F5A524] font-bold">● ACTIVE</span>
                  )}
                </Command.Item>
              ))}
            </Command.Group>

            {/* Live Corridor Trains */}
            <Command.Group heading="Active Trains" className="text-[10px] uppercase text-[#6B7480] px-2 py-1 font-bold">
              {trains.slice(0, 8).map(t => (
                <Command.Item
                  key={t.number}
                  onSelect={() => handleSelectRoute(`/dashboard/trains/${t.number}`)}
                  className="flex items-center justify-between px-2.5 py-2 rounded-sm cursor-pointer text-[#E9EBEE] hover:bg-[#15181D] hover:text-[#F5A524] transition-colors"
                >
                  <div className="flex items-center gap-2 truncate">
                    <Train className="w-3.5 h-3.5 text-[#6B7480]" />
                    <span className="font-bold text-[#F5A524]">{t.number}</span>
                    <span className="truncate text-[11px] text-[#A3ABB6] font-sans">{t.name}</span>
                  </div>
                  <span className="text-[10px] text-[#A3ABB6] shrink-0">PF {t.platform || 1} · {t.predictedArrival || '18:22'}</span>
                </Command.Item>
              ))}
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
