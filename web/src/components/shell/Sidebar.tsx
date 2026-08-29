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

interface NavGroup {
  id: string;
  title: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    id: 'overview',
    title: 'Overview',
    items: [
      { name: 'Control Room', href: '/dashboard', icon: Activity },
    ],
  },
  {
    id: 'operations',
    title: 'Operations',
    items: [
      { name: 'Platform Gantt', href: '/dashboard/gantt', icon: Calendar },
      { name: 'Trains Directory', href: '/dashboard/trains', icon: Train },
      { name: 'Advisory Triage', href: '/dashboard/advisories', icon: Bell, badge: 3, badgeType: 'warn' },
      { name: 'Timetable Manager', href: '/dashboard/timetable', icon: Clock },
      { name: 'Block Sections', href: '/dashboard/blocks', icon: Grid },
      { name: 'Shunting & Loco Moves', href: '/dashboard/shunting', icon: Truck },
    ],
  },
  {
    id: 'network',
    title: 'Network & Yard',
    items: [
      { name: 'Corridor GIS Map', href: '/dashboard/map', icon: Navigation },
      { name: 'Yard Track Diagram', href: '/dashboard/yard-map', icon: Layers },
    ],
  },
  {
    id: 'safety',
    title: 'Safety & Compliance',
    items: [
      { name: 'TSR / Caution Orders', href: '/dashboard/safety/tsr', icon: ShieldAlert, badge: 2, badgeType: 'warn' },
      { name: 'Incident Register', href: '/dashboard/safety/incidents', icon: AlertCircle, badge: 1, badgeType: 'danger' },
      { name: 'Emergency SOP Runner', href: '/dashboard/safety/sop', icon: FileCheck },
      { name: 'Level Crossing Monitor', href: '/dashboard/safety/lc', icon: Shield },
    ],
  },
  {
    id: 'crew',
    title: 'Crew & Workforce',
    items: [
      { name: 'Crew Duty Rosters', href: '/dashboard/crew', icon: Users, badge: 1, badgeType: 'warn' },
    ],
  },
  {
    id: 'infra',
    title: 'Infrastructure',
    items: [
      { name: 'Track-Block Gantt', href: '/dashboard/maintenance', icon: Wrench },
      { name: 'Asset Registry & MTBF', href: '/dashboard/assets', icon: Wrench },
      { name: 'Work Orders Kanban', href: '/dashboard/work-orders', icon: Grid, badge: 1, badgeType: 'danger' },
      { name: 'Cleaning & Turnaround', href: '/dashboard/cleaning', icon: Sparkles },
    ],
  },
  {
    id: 'coord',
    title: 'Coordination',
    items: [
      { name: 'Corridor Handoff', href: '/dashboard/corridor-coordination', icon: Radio },
      { name: 'DFC Freight Precedence', href: '/dashboard/dfc-coordination', icon: Train },
    ],
  },
  {
    id: 'commercial',
    title: 'Commercial & Kiosk',
    items: [
      { name: 'Delay Certificate', href: '/dashboard/commercial/delay-certificate', icon: FileCheck },
      { name: 'PA Announcements', href: '/dashboard/commercial/announcements', icon: Radio },
      { name: 'Stalls & Lost-Found', href: '/dashboard/commercial/stalls', icon: Store },
    ],
  },
  {
    id: 'governance',
    title: 'Governance & Admin',
    items: [
      { name: 'Shift Handover', href: '/dashboard/handover', icon: BookOpen },
      { name: 'Regulatory Audit', href: '/dashboard/audit', icon: Shield },
      { name: 'Model Proof F14', href: '/dashboard/model', icon: FileCode },
      { name: 'User Management', href: '/dashboard/admin/users', icon: UserCheck },
      { name: 'Backups & Integrity', href: '/dashboard/admin/backups', icon: Database },
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

  const handleLogout = () => {
    logoutMockAuth();
    navigate('/login');
  };

  const handleRoleSelect = (roleId: UserRole) => {
    switchUserRole(roleId);
    setIsRoleMenuOpen(false);
    toast.success(`Switched role to ${ROLE_CONFIGS[roleId].name}`);
  };

  // Filter visible groups based on active role
  const visibleGroups = NAV_GROUPS.filter(g =>
    roleConfig.allowedGroups.includes(g.id)
  );

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
            v3.0
          </span>
        </div>

        {/* Grouped Navigation */}
        <nav className="flex-1 overflow-y-auto p-3 space-y-4 font-mono text-xs no-scrollbar">
          {visibleGroups.map(group => (
            <div key={group.id} className="space-y-1">
              <div className="px-2 text-[10px] font-bold text-[#6B6E74] uppercase tracking-wider">
                {group.title}
              </div>
              <div className="space-y-0.5">
                {group.items.map(item => {
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
          ))}
        </nav>

        {/* User & Role Switcher Footer */}
        <div className="border-t border-[#26282C] p-3 space-y-2 bg-[#0E0F11]">
          {/* Role Switcher Button */}
          <div className="relative">
            <button
              onClick={() => setIsRoleMenuOpen(!isRoleMenuOpen)}
              className="w-full bg-[#15171A] border border-[#26282C] hover:border-[#FFB224] p-2 flex items-center justify-between text-left font-mono transition-colors"
            >
              <div>
                <div className="text-[9px] text-[#9A9DA3] uppercase">ACTIVE ROLE VIEW</div>
                <div className="text-[11px] font-bold text-[#FFB224] flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 bg-[#FFB224]" />
                  <span>{roleConfig.shortLabel} · {roleConfig.name}</span>
                </div>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-[#9A9DA3]" />
            </button>

            {/* Role Dropdown */}
            {isRoleMenuOpen && (
              <div className="absolute bottom-full left-0 right-0 mb-1 bg-[#15171A] border border-[#26282C] p-1 space-y-1 shadow-2xl font-mono text-[10px] z-50">
                <div className="px-2 py-1 text-[#9A9DA3] uppercase border-b border-[#26282C] font-semibold">
                  Switch Operational View:
                </div>
                {(Object.keys(ROLE_CONFIGS) as UserRole[]).slice(0, 6).map(r => (
                  <button
                    key={r}
                    onClick={() => handleRoleSelect(r)}
                    className={`w-full text-left px-2 py-1.5 transition-colors flex items-center justify-between ${
                      currentRole === r ? 'bg-[#FFB224] text-[#0E0F11] font-bold' : 'text-[#E8E8E6] hover:bg-[#1B1D21]'
                    }`}
                  >
                    <span>{ROLE_CONFIGS[r].name}</span>
                    <span className="text-[9px] uppercase">[{ROLE_CONFIGS[r].shortLabel}]</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* User Details & Logout */}
          <div className="flex items-center justify-between pt-1 text-xs">
            <div className="truncate">
              <span className="font-mono text-[11px] font-semibold text-[#E8E8E6] truncate block">
                {user?.name || 'Station Master'}
              </span>
              <span className="font-mono text-[10px] text-[#9A9DA3]">
                {user?.station || 'CNB'} Yard
              </span>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={onToggleTheme}
                className="p-1.5 text-[#9A9DA3] hover:text-[#E8E8E6] hover:bg-[#1B1D21]"
                title="Toggle Theme"
              >
                {theme === 'dark' ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
              </button>
              <button
                onClick={handleLogout}
                className="p-1.5 text-[#9A9DA3] hover:text-[#F0533A] hover:bg-[#1B1D21]"
                title="Log out"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
