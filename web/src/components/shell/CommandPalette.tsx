import React, { useEffect, useState } from 'react';
import { Command } from 'cmdk';
import { useNavigate } from 'react-router-dom';
import { mockStore } from '@/mock/store';
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
  const [trains, setTrains] = useState(() => mockStore.getTrains());
  const activeStation = mockStore.getActiveStation();

  useEffect(() => {
    const unsub = mockStore.subscribe(() => {
      setTrains(mockStore.getTrains());
    });
    return unsub;
  }, []);

  const handleSelectRoute = (path: string) => {
    navigate(path);
    onOpenChange(false);
  };

  const handleSelectStation = (code: StationCode) => {
    mockStore.setActiveStation(code, 'CMD_PALETTE');
    onOpenChange(false);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-start justify-center pt-20 p-4">
      <div
        className="w-full max-w-xl bg-[#15171A] border border-[#26282C] shadow-2xl rounded-none overflow-hidden font-mono"
        onClick={e => e.stopPropagation()}
      >
        <Command
          className="w-full bg-transparent text-[#E8E8E6] text-xs"
          loop
        >
          <div className="flex items-center gap-2 px-3 py-2.5 border-b border-[#26282C]">
            <Search className="w-4 h-4 text-[#9A9DA3]" />
            <Command.Input
              autoFocus
              placeholder="Type a module, action, train number (#12301), or station (CNB)..."
              className="w-full bg-transparent text-[#E8E8E6] placeholder-[#9A9DA3] text-xs focus:outline-none"
            />
            <kbd className="text-[10px] text-[#9A9DA3] border border-[#26282C] px-1.5 py-0.5">ESC</kbd>
          </div>

          <Command.List className="max-h-80 overflow-y-auto p-2 space-y-1">
            <Command.Empty className="py-6 text-center text-[#9A9DA3] text-xs">
              No matching modules, actions, or trains found.
            </Command.Empty>

            {/* Quick Actions */}
            <Command.Group heading="Quick Actions" className="text-[10px] uppercase text-[#6B6E74] px-2 py-1 font-bold">
              <Command.Item
                onSelect={() => handleSelectRoute('/dashboard/commercial/delay-certificate')}
                className="flex items-center gap-2 px-2 py-1.5 cursor-pointer text-[#E8E8E6] hover:bg-[#1B1D21] hover:text-[#FFB224] transition-colors"
              >
                <FileCheck className="w-4 h-4 text-[#FFB224]" />
                <span>Issue Digital Delay Certificate (QR)</span>
              </Command.Item>
              <Command.Item
                onSelect={() => handleSelectRoute('/dashboard/safety/sop')}
                className="flex items-center gap-2 px-2 py-1.5 cursor-pointer text-[#E8E8E6] hover:bg-[#1B1D21] hover:text-[#FFB224] transition-colors"
              >
                <ShieldAlert className="w-4 h-4 text-[#F0533A]" />
                <span>Trigger Emergency SOP Protocol</span>
              </Command.Item>
              <Command.Item
                onSelect={() => handleSelectRoute('/dashboard/safety/tsr')}
                className="flex items-center gap-2 px-2 py-1.5 cursor-pointer text-[#E8E8E6] hover:bg-[#1B1D21] hover:text-[#FFB224] transition-colors"
              >
                <Shield className="w-4 h-4 text-[#FFB224]" />
                <span>Issue Caution Order / Speed Restriction</span>
              </Command.Item>
            </Command.Group>

            {/* Navigation Modules */}
            <Command.Group heading="Station Modules" className="text-[10px] uppercase text-[#6B6E74] px-2 py-1 font-bold">
              <Command.Item
                onSelect={() => handleSelectRoute('/dashboard/map')}
                className="flex items-center gap-2 px-2 py-1.5 cursor-pointer text-[#E8E8E6] hover:bg-[#1B1D21] hover:text-[#FFB224] transition-colors"
              >
                <Navigation className="w-4 h-4" />
                <span>Corridor GIS Spatial Map</span>
              </Command.Item>
              <Command.Item
                onSelect={() => handleSelectRoute('/dashboard/yard-map')}
                className="flex items-center gap-2 px-2 py-1.5 cursor-pointer text-[#E8E8E6] hover:bg-[#1B1D21] hover:text-[#FFB224] transition-colors"
              >
                <Layers className="w-4 h-4" />
                <span>Station Yard Micro-Track Layout</span>
              </Command.Item>
              <Command.Item
                onSelect={() => handleSelectRoute('/dashboard/gantt')}
                className="flex items-center gap-2 px-2 py-1.5 cursor-pointer text-[#E8E8E6] hover:bg-[#1B1D21] hover:text-[#FFB224] transition-colors"
              >
                <Calendar className="w-4 h-4" />
                <span>Platform Gantt Scheduler</span>
              </Command.Item>
              <Command.Item
                onSelect={() => handleSelectRoute('/dashboard/timetable')}
                className="flex items-center gap-2 px-2 py-1.5 cursor-pointer text-[#E8E8E6] hover:bg-[#1B1D21] hover:text-[#FFB224] transition-colors"
              >
                <Clock className="w-4 h-4" />
                <span>Working Timetable (WTT) Manager</span>
              </Command.Item>
              <Command.Item
                onSelect={() => handleSelectRoute('/dashboard/blocks')}
                className="flex items-center gap-2 px-2 py-1.5 cursor-pointer text-[#E8E8E6] hover:bg-[#1B1D21] hover:text-[#FFB224] transition-colors"
              >
                <Grid className="w-4 h-4" />
                <span>Block Section Line Clear Board</span>
              </Command.Item>
              <Command.Item
                onSelect={() => handleSelectRoute('/dashboard/handover')}
                className="flex items-center gap-2 px-2 py-1.5 cursor-pointer text-[#E8E8E6] hover:bg-[#1B1D21] hover:text-[#FFB224] transition-colors"
              >
                <BookOpen className="w-4 h-4" />
                <span>Shift Handover Logbook</span>
              </Command.Item>
              <Command.Item
                onSelect={() => handleSelectRoute('/kiosk')}
                className="flex items-center gap-2 px-2 py-1.5 cursor-pointer text-[#E8E8E6] hover:bg-[#1B1D21] hover:text-[#FFB224] transition-colors"
              >
                <Activity className="w-4 h-4 text-[#3ECF8E]" />
                <span>Station Kiosk PIDS Screen (3m View)</span>
              </Command.Item>
            </Command.Group>

            {/* Stations Switcher */}
            <Command.Group heading="Switch Operational Station" className="text-[10px] uppercase text-[#6B6E74] px-2 py-1 font-bold">
              {(['CNB', 'NDLS', 'GZB'] as StationCode[]).map(code => (
                <Command.Item
                  key={code}
                  onSelect={() => handleSelectStation(code)}
                  className="flex items-center justify-between px-2 py-1.5 cursor-pointer text-[#E8E8E6] hover:bg-[#1B1D21] hover:text-[#FFB224] transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <MapPin className="w-3.5 h-3.5" />
                    <span>{code} Station Yard</span>
                  </div>
                  {activeStation === code && (
                    <span className="text-[10px] text-[#FFB224] font-bold">ACTIVE</span>
                  )}
                </Command.Item>
              ))}
            </Command.Group>

            {/* Live Corridor Trains */}
            <Command.Group heading="Tracked Corridor Trains" className="text-[10px] uppercase text-[#6B6E74] px-2 py-1 font-bold">
              {trains.slice(0, 10).map(t => (
                <Command.Item
                  key={t.number}
                  onSelect={() => handleSelectRoute(`/dashboard/trains/${t.number}`)}
                  className="flex items-center justify-between px-2 py-1.5 cursor-pointer text-[#E8E8E6] hover:bg-[#1B1D21] hover:text-[#FFB224] transition-colors"
                >
                  <div className="flex items-center gap-2 truncate">
                    <Train className="w-3.5 h-3.5 text-[#9A9DA3]" />
                    <span className="font-bold text-[#FFB224]">{t.number}</span>
                    <span className="truncate text-[11px] text-[#E8E8E6]">{t.name}</span>
                  </div>
                  <span className="text-[10px] text-[#9A9DA3] shrink-0">PF {t.platform} · {t.predictedArrival}</span>
                </Command.Item>
              ))}
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
