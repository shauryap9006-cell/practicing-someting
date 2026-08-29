import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { Users, UserPlus, Shield, CheckCircle, Lock } from 'lucide-react';
import { toast } from 'sonner';

interface UserRecord {
  id: string;
  username: string;
  full_name: string;
  email: string;
  role_id: string;
  station_code: string;
  is_active: boolean;
  last_login: string;
}

const ROLE_PERMISSIONS: Record<string, string[]> = {
  admin: ['All Groups (Full Administrative Control)'],
  station_master: ['Overview', 'Operations', 'Network', 'Safety', 'Crew', 'Infrastructure', 'Commercial', 'Governance'],
  section_controller: ['Overview', 'Operations (Read)', 'Network', 'Coordination', 'Safety (TSR Read)'],
  crew_controller: ['Overview', 'Crew', 'Operations (Read)'],
  commercial_inspector: ['Overview', 'Commercial', 'Operations (Read)'],
  engineer: ['Overview', 'Network (Yard)', 'Infrastructure', 'Safety (TSR Read)'],
};

export function AdminUsersPage() {
  const [users, setUsers] = useState<UserRecord[]>([]);

  useEffect(() => {
    api.getUsers().then(data => setUsers(data as UserRecord[]));
  }, []);

  return (
    <div className="space-y-4 font-mono text-xs">
      <SEO title="RBAC Users & Roles Management · RailTwin-X" noindex />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <Users className="w-4 h-4 text-[#FFB224]" />
            <span>Role-Based Access Control (RBAC) & User Management</span>
          </h1>
          <p className="text-[#9A9DA3]">
            System credentials, role permission matrix, and active station assignments
          </p>
        </div>

        <button
          onClick={() => toast.info('Add User dialog is available in production server mode.')}
          className="px-3 py-1.5 bg-[#FFB224] hover:bg-[#E59F1C] text-[#0E0F11] font-bold text-xs flex items-center gap-1.5 transition-colors"
        >
          <UserPlus className="w-3.5 h-3.5" />
          <span>Provision New User</span>
        </button>
      </div>

      {/* Users Table */}
      <div className="bg-[#15171A] border border-[#26282C] p-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#26282C] bg-[#1B1D21] text-[#9A9DA3] text-[11px] uppercase">
                <th className="py-2.5 px-3">Username</th>
                <th className="py-2.5 px-3">Full Name</th>
                <th className="py-2.5 px-3">Email Address</th>
                <th className="py-2.5 px-3">Role</th>
                <th className="py-2.5 px-3 text-center">Station</th>
                <th className="py-2.5 px-3 text-center">Status</th>
                <th className="py-2.5 px-3 text-right">Last Login</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#26282C]">
              {users.map(u => (
                <tr key={u.id} className="hover:bg-[#1B1D21]/50 text-[#E8E8E6]">
                  <td className="py-3 px-3 font-bold text-[#FFB224]">{u.username}</td>
                  <td className="py-3 px-3 font-semibold">{u.full_name}</td>
                  <td className="py-3 px-3 text-[#9A9DA3]">{u.email}</td>
                  <td className="py-3 px-3">
                    <span className="text-[10px] px-2 py-0.5 border border-[#FFB224] text-[#FFB224] bg-[#FFB224]/10 font-bold uppercase">
                      {u.role_id.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-center font-bold">{u.station_code}</td>
                  <td className="py-3 px-3 text-center">
                    <span className="text-[10px] px-1.5 py-0.5 border border-[#3ECF8E] text-[#3ECF8E] bg-[#3ECF8E]/10">
                      ACTIVE
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right text-[#9A9DA3]">{u.last_login}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Role Capability Matrix Panel */}
      <div className="bg-[#15171A] border border-[#26282C] p-5 space-y-3">
        <div className="font-bold text-sm text-[#E8E8E6] flex items-center gap-2 border-b border-[#26282C] pb-2">
          <Shield className="w-4 h-4 text-[#3ECF8E]" />
          <span>Role Capability & Navigation Visibility Matrix</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-2">
          {Object.entries(ROLE_PERMISSIONS).map(([role, groups]) => (
            <div key={role} className="bg-[#0E0F11] border border-[#26282C] p-3 space-y-1">
              <span className="text-[11px] font-bold text-[#FFB224] uppercase block">
                {role.replace('_', ' ')}
              </span>
              <div className="text-[11px] text-[#9A9DA3]">
                {groups.join(' · ')}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
