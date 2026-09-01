import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { getCurrentSession, logoutMockAuth, switchUserRole, ROLE_CONFIGS, UserRole } from '@/mock/auth';
import {
  Activity,
  Calendar,
  Train,
  Bell,
  Users,
  Wrench,
  Shield,
  FileCode,
  LogOut,
  ChevronDown,
  ChevronRight,
  Moon,
  Sun,
  Layers,
  Grid,
  Clock,
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
  Navigation,
} from 'lucide-react';
import { toast } from 'sonner';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number | string;
  badgeType?: 'danger' | 'warn' | 'neutral';
}

// 7 Primary Core Operational Views (Phase C2 Focus Cut)
const PRIMARY_NAV_ITEMS: NavItem[] = [
  { name: 'Overview', href: '/dashboard', icon: Activity },
  { name: 'Live Map', href: '/dashboard/live-map', icon: Navigation, badge: 'LIVE', badgeType: 'warn' },
  { name: 'Trains Directory', href: '/dashboard/trains', icon: Train },
  { name: 'Platform Gantt', href: '/dashboard/gantt', icon: Calendar },
  { name: 'Advisories', href: '/dashboard/advisories', icon: Bell, badge: 3, badgeType: 'warn' },
  { name: 'Model & Proof', href: '/dashboard/model', icon: FileCode },
  { name: 'Public Kiosk', href: '/kiosk', icon: Store },
];

// Collapsible Advanced Views
const ADVANCED_NAV_GROUPS: Array<{ title: string; items: NavItem[] }> = [
  {
    title: 'Operations & Track',
    items: [
      { name: 'Timetable Manager', href: '/dashboard/timetable', icon: Clock },
      { name: 'Block Sections', href: '/dashboard/blocks', icon: Grid },
      { name: 'Shunting & Moves', href: '/dashboard/shunting', icon: Truck },
      { name: 'Yard Diagram', href: '/dashboard/yard-map', icon: Layers },
    ],
  },
  {
    title: 'Safety & Compliance',
    items: [
      { name: 'TSR / Caution Orders', href: '/dashboard/safety/tsr', icon: ShieldAlert, badge: 2, badgeType: 'warn' },
      { name: 'Incident Register', href: '/dashboard/safety/incidents', icon: AlertCircle, badge: 1, badgeType: 'danger' },
      { name: 'Emergency SOP', href: '/dashboard/safety/sop', icon: FileCheck },
      { name: 'LC Gate Monitor', href: '/dashboard/safety/lc', icon: Shield },
    ],
  },
  {
    title: 'Workforce & Infra',
    items: [
      { name: 'Crew Rosters', href: '/dashboard/crew', icon: Users },
      { name: 'Track-Block Gantt', href: '/dashboard/maintenance', icon: Wrench },
      { name: 'Asset MTBF', href: '/dashboard/assets', icon: Wrench },
      { name: 'Work Orders', href: '/dashboard/work-orders', icon: Grid, badge: 1, badgeType: 'danger' },
      { name: 'Cleaning & Turn', href: '/dashboard/cleaning', icon: Sparkles },
    ],
  },
  {
    title: 'Coordination & Commercial',
    items: [
      { name: 'Corridor Handoff', href: '/dashboard/corridor-coordination', icon: Radio },
      { name: 'DFC Precedence', href: '/dashboard/dfc-coordination', icon: Train },
      { name: 'Delay Certificate', href: '/dashboard/commercial/delay-certificate', icon: FileCheck },
      { name: 'PA Announcements', href: '/dashboard/commercial/announcements', icon: Radio },
      { name: 'Stalls & Lost/Found', href: '/dashboard/commercial/stalls', icon: Store },
    ],
  },
  {
    title: 'Governance & Admin',
    items: [
      { name: 'Shift Handover', href: '/dashboard/handover', icon: BookOpen },
      { name: 'Regulatory Audit', href: '/dashboard/audit', icon: Shield },
      { name: 'User Management', href: '/dashboard/admin/users', icon: UserCheck },
      { name: 'Backups & DB', href: '/dashboard/admin/backups', icon: Database },
    ],
  },
];

export function Sidebar({
  isOpen,
  onClose,
  theme,
  onToggleTheme,
}: {
  isOpen: boolean;
  onClose: () => void;
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
}) {
  const navigate = useNavigate();
  const session = getCurrentSession();
  const user = session?.user;
  const currentRole = (user?.role as UserRole) || 'station_master';
  const roleConfig = ROLE_CONFIGS[currentRole] || ROLE_CONFIGS.station_master;

  const [isRoleMenuOpen, setIsRoleMenuOpen] = useState(false);
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);

  const handleLogout = () => {
    logoutMockAuth();
    navigate('/login');
  };

  const handleRoleSelect = (roleId: UserRole) => {
    switchUserRole(roleId);
    setIsRoleMenuOpen(false);
    toast.success(`Switched role to ${ROLE_CONFIGS[roleId].name}`);
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 w-60 bg-[#15171A] border-r border-[#26282C] flex flex-col transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="h-12 border-b border-[#26282C] flex items-center justify-between px-4 bg-[#0E0F11]">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-[#FFB224]" />
            <span className="font-sans font-bold text-sm tracking-tight text-[#E8E8E6]">
              RailTwin-X
            </span>
          </div>
          <span className="font-mono text-[10px] uppercase tracking-wider text-[#FFB224] border border-[#FFB224]/30 px-1.5 py-0.2">
            v3.0 LIVE
          </span>
        </div>

        {/* Navigation Content */}
        <nav className="flex-1 overflow-y-auto p-3 space-y-4 font-mono text-xs no-scrollbar">
          {/* Primary 7 Focus Views */}
          <div className="space-y-1">
            <div className="px-2 text-[10px] font-bold text-[#6B6E74] uppercase tracking-wider">
              Primary Views
            </div>
            <div className="space-y-0.5">
              {PRIMARY_NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.href}
                    to={item.href}
                    end={item.href === '/dashboard'}
                    onClick={() => {
                      if (window.innerWidth < 1024) onClose();
                    }}
                    className={({ isActive }) =>
                      `flex items-center justify-between px-2 py-1.5 rounded-none transition-colors group ${
                        isActive
                          ? 'bg-[#1B1D21] text-[#FFB224] border-l-2 border-[#FFB224] font-semibold pl-2.5'
                          : 'text-[#9A9DA3] hover:bg-[#1B1D21] hover:text-[#E8E8E6]'
                      }`
                    }
                  >
                    <div className="flex items-center gap-2 truncate">
                      <Icon className="w-4 h-4 shrink-0" />
                      <span className="truncate text-[11px]">{item.name}</span>
                    </div>

                    {item.badge !== undefined && (
                      <span
                        className={`text-[9px] px-1 py-0.2 border ${
                          item.badgeType === 'danger'
                            ? 'border-[#F0533A] text-[#F0533A] bg-[#F0533A]/10'
                            : item.badgeType === 'warn'
                            ? 'border-[#FFB224] text-[#FFB224] bg-[#FFB224]/10'
                            : 'border-[#26282C] text-[#9A9DA3]'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>

          {/* Collapsible Advanced Group */}
          <div className="pt-2 border-t border-[#26282C]/60 space-y-2">
            <button
              onClick={() => setIsAdvancedOpen(!isAdvancedOpen)}
              className="w-full flex items-center justify-between px-2 py-1.5 text-[10px] font-bold text-[#6B6E74] hover:text-[#E8E8E6] uppercase tracking-wider rounded transition-colors"
            >
              <span>Advanced Operations</span>
              {isAdvancedOpen ? (
                <ChevronDown className="w-3.5 h-3.5" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5" />
              )}
            </button>

            {isAdvancedOpen && (
              <div className="space-y-3 pl-1 pt-1 animate-in fade-in duration-200">
                {ADVANCED_NAV_GROUPS.map((group) => (
                  <div key={group.title} className="space-y-1">
                    <div className="px-2 text-[9px] font-bold text-[#4B4E54] uppercase tracking-wider">
                      {group.title}
                    </div>
                    <div className="space-y-0.5">
                      {group.items.map((item) => {
                        const Icon = item.icon;
                        return (
                          <NavLink
                            key={item.href}
                            to={item.href}
                            onClick={() => {
                              if (window.innerWidth < 1024) onClose();
                            }}
                            className={({ isActive }) =>
                              `flex items-center justify-between px-2 py-1 rounded-none transition-colors group ${
                                isActive
                                  ? 'bg-[#1B1D21] text-[#FFB224] border-l-2 border-[#FFB224] font-semibold pl-2.5'
                                  : 'text-[#8A8D93] hover:bg-[#1B1D21] hover:text-[#E8E8E6]'
                              }`
                            }
                          >
                            <div className="flex items-center gap-2 truncate">
                              <Icon className="w-3.5 h-3.5 shrink-0 text-[#6B6E74] group-hover:text-[#E8E8E6]" />
                              <span className="truncate text-[10px]">{item.name}</span>
                            </div>

                            {item.badge !== undefined && (
                              <span className="text-[8px] px-1 py-0.2 border border-[#26282C] text-[#8A8D93]">
                                {item.badge}
                              </span>
                            )}
                          </NavLink>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </nav>

        {/* User & Role Switcher Footer */}
        <div className="border-t border-[#26282C] p-3 space-y-2 bg-[#0E0F11]">
          {/* Active Role Card */}
          <div className="relative">
            <button
              onClick={() => setIsRoleMenuOpen(!isRoleMenuOpen)}
              className="w-full flex items-center justify-between p-1.5 bg-[#15171A] border border-[#26282C] hover:border-[#FFB224]/50 transition-colors text-left"
            >
              <div className="truncate">
                <div className="font-sans font-semibold text-xs text-[#E8E8E6] truncate">
                  {user?.name || 'Dispatcher'}
                </div>
                <div className="font-mono text-[10px] text-[#FFB224] flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#FFB224]" />
                  <span>{roleConfig.name}</span>
                </div>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-[#6B6E74]" />
            </button>

            {/* Role Switcher Menu */}
            {isRoleMenuOpen && (
              <div className="absolute bottom-full left-0 right-0 mb-1 bg-[#15171A] border border-[#26282C] shadow-xl z-50 p-1 space-y-0.5">
                <div className="px-2 py-1 text-[9px] font-bold text-[#6B6E74] uppercase border-b border-[#26282C]">
                  Switch Operating Role
                </div>
                {Object.entries(ROLE_CONFIGS).map(([key, config]) => (
                  <button
                    key={key}
                    onClick={() => handleRoleSelect(key as UserRole)}
                    className={`w-full text-left px-2 py-1 text-[11px] font-mono flex items-center justify-between ${
                      currentRole === key
                        ? 'bg-[#FFB224]/10 text-[#FFB224] font-bold'
                        : 'text-[#9A9DA3] hover:bg-[#1B1D21] hover:text-[#E8E8E6]'
                    }`}
                  >
                    <span>{config.name}</span>
                    {currentRole === key && <span className="text-[9px]">&check;</span>}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Theme & Logout Actions */}
          <div className="flex items-center justify-between text-xs font-mono text-[#6B6E74] pt-1">
            <button
              onClick={onToggleTheme}
              className="flex items-center gap-1.5 hover:text-[#E8E8E6] transition-colors p-1"
              title="Toggle Theme"
            >
              {theme === 'dark' ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
              <span className="text-[10px]">{theme === 'dark' ? 'Light' : 'Dark'}</span>
            </button>

            <button
              onClick={handleLogout}
              className="flex items-center gap-1 text-[#F0533A] hover:underline p-1 text-[10px]"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
