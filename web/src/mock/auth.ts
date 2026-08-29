import { UserSession, StationCode } from './types';

export const SESSION_KEY = 'rtx-session';
const SESSION_DURATION_MS = 12 * 60 * 60 * 1000; // 12 hours

export type UserRole =
  | 'admin'
  | 'station_master'
  | 'section_controller'
  | 'crew_controller'
  | 'commercial_inspector'
  | 'engineer'
  | 'dy_sm'
  | 'tte'
  | 'viewer';

export interface AuthUser {
  id: string;
  username: string;
  email: string;
  name: string;
  role: UserRole;
  roleName: string;
  station: StationCode;
  stationName: string;
  token?: string;
}

export interface RoleConfig {
  id: UserRole;
  name: string;
  shortLabel: string;
  description: string;
  allowedGroups: string[];
}

export const ROLE_CONFIGS: Record<UserRole, RoleConfig> = {
  admin: {
    id: 'admin',
    name: 'System Administrator',
    shortLabel: 'ADMIN',
    description: 'Full administrative control, user management, backups, and audit verification.',
    allowedGroups: ['overview', 'operations', 'network', 'safety', 'crew', 'infra', 'coord', 'commercial', 'governance'],
  },
  station_master: {
    id: 'station_master',
    name: 'Station Master (SM)',
    shortLabel: 'SM',
    description: 'Supreme operational command over station, Gantt re-optimization, shift handover, and safety.',
    allowedGroups: ['overview', 'operations', 'network', 'safety', 'crew', 'infra', 'coord', 'commercial', 'governance'],
  },
  section_controller: {
    id: 'section_controller',
    name: 'Section Controller',
    shortLabel: 'CTRL',
    description: 'Corridor block line clearance, precedence regulation, and inter-station coordination.',
    allowedGroups: ['overview', 'operations', 'network', 'coord', 'safety'],
  },
  crew_controller: {
    id: 'crew_controller',
    name: 'Crew Controller',
    shortLabel: 'CREW',
    description: 'Crew rostering, duty breach lookahead, relief dispatch, and sign-on/off tracking.',
    allowedGroups: ['overview', 'crew', 'operations'],
  },
  commercial_inspector: {
    id: 'commercial_inspector',
    name: 'Commercial Inspector',
    shortLabel: 'COMM',
    description: 'Delay certificates, public address announcements, stall leases, and kiosk.',
    allowedGroups: ['overview', 'commercial', 'operations'],
  },
  engineer: {
    id: 'engineer',
    name: 'Signal & Track Engineer',
    shortLabel: 'ENG',
    description: 'Track assets, points, signals, OHE 25kV spans, and work orders Kanban.',
    allowedGroups: ['overview', 'network', 'infra', 'safety'],
  },
  dy_sm: {
    id: 'dy_sm',
    name: 'Deputy Station Master',
    shortLabel: 'Dy.SM',
    description: 'Shift supervisor, platform operations, set-in/out, and incident recording.',
    allowedGroups: ['overview', 'operations', 'network', 'safety', 'crew'],
  },
  tte: {
    id: 'tte',
    name: 'Head TTE',
    shortLabel: 'TTE',
    description: 'Passenger ticket verification and delay certificates.',
    allowedGroups: ['overview', 'commercial', 'operations'],
  },
  viewer: {
    id: 'viewer',
    name: 'Operations Observer',
    shortLabel: 'VIEW',
    description: 'Read-only corridor observer.',
    allowedGroups: ['overview', 'network'],
  },
};

export const DEMO_USERS: Array<AuthUser & { password: string }> = [
  {
    id: 'usr-sm-ndls-01',
    username: 'sm_ndls',
    email: 'sm@cnb.railtwin.app',
    password: 'demo1234',
    name: 'Rajesh Kumar (Station Master)',
    role: 'station_master',
    roleName: 'Station Master (SM)',
    station: 'CNB',
    stationName: 'Kanpur Central (CNB)',
  },
  {
    id: 'usr-section-ctrl-01',
    username: 'section_ctrl',
    email: 'controller@railtwin.app',
    password: 'demo1234',
    name: 'Vikram Seth (Section Controller)',
    role: 'section_controller',
    roleName: 'Section Controller',
    station: 'CNB',
    stationName: 'Kanpur Central (CNB)',
  },
  {
    id: 'usr-crew-ctrl-01',
    username: 'crew_ctrl',
    email: 'crew@railtwin.app',
    password: 'demo1234',
    name: 'Suresh Raina (Crew Controller)',
    role: 'crew_controller',
    roleName: 'Crew Controller',
    station: 'CNB',
    stationName: 'Kanpur Central (CNB)',
  },
  {
    id: 'usr-comm-01',
    username: 'comm_inspector',
    email: 'commercial@railtwin.app',
    password: 'demo1234',
    name: 'Ananya Roy (Commercial Inspector)',
    role: 'commercial_inspector',
    roleName: 'Commercial Inspector',
    station: 'CNB',
    stationName: 'Kanpur Central (CNB)',
  },
  {
    id: 'usr-eng-01',
    username: 'engineer_track',
    email: 'engineer@railtwin.app',
    password: 'demo1234',
    name: 'Er. Priya Patel (Signal & Track Engineer)',
    role: 'engineer',
    roleName: 'Signal & Track Engineer',
    station: 'CNB',
    stationName: 'Kanpur Central (CNB)',
  },
  {
    id: 'usr-admin-01',
    username: 'admin',
    email: 'admin@railtwin.app',
    password: 'demo1234',
    name: 'Chief System Administrator',
    role: 'admin',
    roleName: 'System Administrator',
    station: 'NDLS',
    stationName: 'New Delhi (NDLS)',
  },
];

export async function loginWithMockAuth(usernameOrEmail: string, password: string): Promise<UserSession> {
  const cleanInput = usernameOrEmail.trim().toLowerCase();

  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  // Try real FastAPI backend first
  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: cleanInput, password }),
    });


    if (res.ok) {
      const data = await res.json();
      const session: UserSession = {
        user: {
          id: data.user.id,
          username: data.user.username,
          email: data.user.email || `${data.user.username}@railtwin.app`,
          name: data.user.full_name,
          role: (data.user.role_id as UserRole) || 'station_master',
          roleName: data.user.role_name || 'Station Master',
          station: (data.user.station_code as StationCode) || 'CNB',
          stationName: `${data.user.station_code} Station`,
          token: data.access_token,
        },
        expiresAt: Date.now() + SESSION_DURATION_MS,
      };

      if (typeof window !== 'undefined') {
        localStorage.setItem(SESSION_KEY, JSON.stringify(session));
      }
      return session;
    }
  } catch {
    // FastAPI server not reachable or network error -> use deterministic fallback
  }

  // Fallback to local demo users
  await new Promise(resolve => setTimeout(resolve, 300));
  const user = DEMO_USERS.find(
    u => u.username.toLowerCase() === cleanInput || u.email.toLowerCase() === cleanInput
  );

  if (!user) {
    throw new Error('Invalid credentials. Select a demo role above.');
  }

  const session: UserSession = {
    user: {
      id: user.id,
      username: user.username,
      email: user.email,
      name: user.name,
      role: user.role,
      roleName: user.roleName,
      station: user.station,
      stationName: user.stationName,
      token: 'demo-jwt-token-sih-2026',
    },
    expiresAt: Date.now() + SESSION_DURATION_MS,
  };

  if (typeof window !== 'undefined') {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  }

  return session;
}

export function getCurrentSession(): UserSession | null {
  if (typeof window === 'undefined') return null;

  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return null;

  try {
    const session = JSON.parse(raw) as UserSession;
    if (!session || !session.expiresAt || Date.now() > session.expiresAt) {
      localStorage.removeItem(SESSION_KEY);
      return null;
    }
    return session;
  } catch {
    localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function switchUserRole(roleId: UserRole): UserSession | null {
  const current = getCurrentSession();
  if (!current) return null;

  const targetDemoUser = DEMO_USERS.find(u => u.role === roleId) || DEMO_USERS[0];
  const updatedSession: UserSession = {
    ...current,
    user: {
      ...current.user,
      id: targetDemoUser.id,
      name: targetDemoUser.name,
      role: targetDemoUser.role,
      roleName: targetDemoUser.roleName,
      username: targetDemoUser.username,
    },
  };

  if (typeof window !== 'undefined') {
    localStorage.setItem(SESSION_KEY, JSON.stringify(updatedSession));
    window.dispatchEvent(new Event('storage'));
  }
  return updatedSession;
}

export function logoutMockAuth(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(SESSION_KEY);
}
