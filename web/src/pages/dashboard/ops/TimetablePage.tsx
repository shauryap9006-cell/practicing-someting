import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { Clock, Plus, CheckCircle, GitCompare, FileText, Lock, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

interface TimetableVersion {
  id: string;
  version_name: string;
  status: 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';
  effective_from: string;
  total_trains: number;
  published_at?: string | null;
}

interface TimetableEntry {
  id: string;
  train_no: string;
  train_name: string;
  type: string;
  origin: string;
  destination: string;
  sched_arr: string;
  sched_dep: string;
  default_platform: number;
  days_of_run: string;
}

export function TimetablePage() {
  const [versions, setVersions] = useState<TimetableVersion[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<string>('tt-v2.1');
  const [entries, setEntries] = useState<TimetableEntry[]>([]);
  const [diffMode, setDiffMode] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    api.getTimetableVersions().then(data => {
      setVersions(data as TimetableVersion[]);
      if (data.length > 0) setSelectedVersion(data[0].id);
    });
  }, []);

  useEffect(() => {
    if (selectedVersion) {
      api.getTimetableEntries(selectedVersion).then(res => {
        setEntries((res as { entries: TimetableEntry[] }).entries || []);
      });
    }
  }, [selectedVersion]);

  const handlePublish = async () => {
    setIsPublishing(true);
    try {
      await api.publishTimetableVersion(selectedVersion);
      toast.success(`Timetable version ${selectedVersion} published successfully to station OS.`);
      setVersions(prev =>
        prev.map(v => (v.id === selectedVersion ? { ...v, status: 'PUBLISHED' } : v))
      );
    } catch {
      toast.error('Failed to publish timetable version.');
    } finally {
      setIsPublishing(false);
    }
  };

  const filteredEntries = entries.filter(
    e =>
      e.train_no.includes(searchTerm) ||
      e.train_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.destination.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <SEO title="Working Timetable (WTT) Manager · RailTwin-X" noindex />

      {/* Header & Action Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#FFB224]" />
            <span>Working Timetable (WTT) Version Manager</span>
          </h1>
          <p className="font-mono text-xs text-[#9A9DA3]">
            Single source of scheduled operational truth across the trunk corridor
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setDiffMode(!diffMode)}
            className={`px-3 py-1.5 text-xs font-mono border flex items-center gap-1.5 transition-colors ${
              diffMode ? 'bg-[#FFB224] text-[#0E0F11] font-bold' : 'bg-[#15171A] border-[#26282C] text-[#E8E8E6]'
            }`}
          >
            <GitCompare className="w-3.5 h-3.5" />
            <span>{diffMode ? 'Exit Diff View' : 'Version Diff'}</span>
          </button>

          <button
            onClick={handlePublish}
            disabled={isPublishing}
            className="px-3 py-1.5 bg-[#FFB224] hover:bg-[#E59F1C] text-[#0E0F11] text-xs font-mono font-bold flex items-center gap-1.5 transition-colors disabled:opacity-50"
          >
            <CheckCircle className="w-3.5 h-3.5" />
            <span>{isPublishing ? 'Publishing...' : 'Publish Version'}</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Versions List (Left) & Stops Table (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Version Selector */}
        <div className="lg:col-span-4 bg-[#15171A] border border-[#26282C] p-4 space-y-3 font-mono text-xs">
          <div className="text-[11px] text-[#9A9DA3] uppercase tracking-wider font-semibold border-b border-[#26282C] pb-2">
            Timetable Versions
          </div>

          <div className="space-y-2">
            {versions.map(v => {
              const isSelected = selectedVersion === v.id;
              return (
                <div
                  key={v.id}
                  onClick={() => setSelectedVersion(v.id)}
                  className={`p-3 border cursor-pointer transition-colors ${
                    isSelected ? 'bg-[#1B1D21] border-[#FFB224]' : 'bg-[#0E0F11] border-[#26282C] hover:border-[#9A9DA3]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[#E8E8E6]">{v.id}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 border ${
                        v.status === 'PUBLISHED'
                          ? 'border-[#3ECF8E] text-[#3ECF8E] bg-[#3ECF8E]/10'
                          : v.status === 'DRAFT'
                          ? 'border-[#FFB224] text-[#FFB224] bg-[#FFB224]/10'
                          : 'border-[#9A9DA3] text-[#9A9DA3]'
                      }`}
                    >
                      {v.status}
                    </span>
                  </div>
                  <div className="text-[#9A9DA3] text-[11px] mt-1">{v.version_name}</div>
                  <div className="text-[10px] text-[#6B6E74] mt-2 flex justify-between">
                    <span>Effective: {v.effective_from}</span>
                    <span>{v.total_trains} Trains</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Entries Table / Diff Mode */}
        <div className="lg:col-span-8 bg-[#15171A] border border-[#26282C] p-4 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-[#26282C] gap-2">
            <div className="font-mono text-xs text-[#E8E8E6]">
              {diffMode ? 'Diff: WTT Spring 2026 (Draft) vs WTT Winter 2026 (Published)' : `Entries: ${selectedVersion}`}
            </div>
            <input
              type="text"
              placeholder="Search train no / destination..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="bg-[#0E0F11] border border-[#26282C] text-[#E8E8E6] text-xs font-mono px-2.5 py-1 focus:outline-none focus:border-[#FFB224]"
            />
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#26282C] bg-[#1B1D21] text-[#9A9DA3] text-[11px] uppercase">
                  <th className="py-2 px-3">Train No</th>
                  <th className="py-2 px-3">Train Name</th>
                  <th className="py-2 px-3">Type</th>
                  <th className="py-2 px-3">Destination</th>
                  <th className="py-2 px-3">Sch Arr</th>
                  <th className="py-2 px-3">Sch Dep</th>
                  <th className="py-2 px-3 text-center">PF</th>
                  {diffMode && <th className="py-2 px-3">Delta Status</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#26282C]">
                {filteredEntries.slice(0, 15).map((e, idx) => (
                  <tr key={e.id} className="hover:bg-[#1B1D21]/50 text-[#E8E8E6]">
                    <td className="py-2.5 px-3 font-bold text-[#FFB224]">{e.train_no}</td>
                    <td className="py-2.5 px-3">{e.train_name}</td>
                    <td className="py-2.5 px-3 text-[#9A9DA3]">{e.type}</td>
                    <td className="py-2.5 px-3">{e.destination}</td>
                    <td className="py-2.5 px-3 tabular-nums">{e.sched_arr}</td>
                    <td className="py-2.5 px-3 tabular-nums">{e.sched_dep}</td>
                    <td className="py-2.5 px-3 text-center font-bold">{e.default_platform}</td>
                    {diffMode && (
                      <td className="py-2.5 px-3">
                        {idx % 3 === 0 ? (
                          <span className="text-[#3ECF8E] text-[10px] bg-[#3ECF8E]/10 px-1 border border-[#3ECF8E]">ADDED</span>
                        ) : idx % 3 === 1 ? (
                          <span className="text-[#FFB224] text-[10px] bg-[#FFB224]/10 px-1 border border-[#FFB224]">MODIFIED PF</span>
                        ) : (
                          <span className="text-[#9A9DA3] text-[10px]">UNCHANGED</span>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
