import { Station, PlatformInfo } from './types';

export const STATIONS: Record<string, Station> = {
  CNB: {
    code: 'CNB',
    name: 'Kanpur Central',
    fullName: 'Kanpur Central Junction (NCR / Prayagraj Div)',
    division: 'Prayagraj (PRYJ)',
    zone: 'North Central Railway (NCR)',
    platformsCount: 10,
    activeTrainsCount: 38,
    platformConflictsCount: 2,
    pendingAdvisoriesCount: 4,
    crewWarningsCount: 3,
    corridorAvgDelayMinutes: 14.8,
  },
  NDLS: {
    code: 'NDLS',
    name: 'New Delhi',
    fullName: 'New Delhi Railway Station (NR / Delhi Div)',
    division: 'Delhi (DLI)',
    zone: 'Northern Railway (NR)',
    platformsCount: 16,
    activeTrainsCount: 52,
    platformConflictsCount: 1,
    pendingAdvisoriesCount: 3,
    crewWarningsCount: 2,
    corridorAvgDelayMinutes: 9.4,
  },
  GZB: {
    code: 'GZB',
    name: 'Ghaziabad',
    fullName: 'Ghaziabad Junction (NR / Delhi Div)',
    division: 'Delhi (DLI)',
    zone: 'Northern Railway (NR)',
    platformsCount: 6,
    activeTrainsCount: 24,
    platformConflictsCount: 1,
    pendingAdvisoriesCount: 2,
    crewWarningsCount: 1,
    corridorAvgDelayMinutes: 11.2,
  },
};

export const INITIAL_PLATFORMS_CNB: PlatformInfo[] = [
  { platformNumber: 1, lengthMeters: 650, isElectrified: true, maxSpeedKmph: 30, hasWatering: true, slots: [] },
  { platformNumber: 2, lengthMeters: 620, isElectrified: true, maxSpeedKmph: 30, hasWatering: true, slots: [] },
  { platformNumber: 3, lengthMeters: 640, isElectrified: true, maxSpeedKmph: 30, hasWatering: true, slots: [] },
  { platformNumber: 4, lengthMeters: 600, isElectrified: true, maxSpeedKmph: 30, hasWatering: false, slots: [] },
  { platformNumber: 5, lengthMeters: 590, isElectrified: true, maxSpeedKmph: 30, hasWatering: false, slots: [] },
  { platformNumber: 6, lengthMeters: 550, isElectrified: true, maxSpeedKmph: 30, hasWatering: false, slots: [] },
  { platformNumber: 7, lengthMeters: 580, isElectrified: true, maxSpeedKmph: 30, hasWatering: true, slots: [] },
  { platformNumber: 8, lengthMeters: 600, isElectrified: true, maxSpeedKmph: 30, hasWatering: true, slots: [] },
  { platformNumber: 9, lengthMeters: 620, isElectrified: true, maxSpeedKmph: 30, hasWatering: false, slots: [] },
  { platformNumber: 10, lengthMeters: 650, isElectrified: true, maxSpeedKmph: 30, hasWatering: true, slots: [] },
];

export const INITIAL_PLATFORMS_NDLS: PlatformInfo[] = Array.from({ length: 16 }, (_, i) => ({
  platformNumber: i + 1,
  lengthMeters: 680,
  isElectrified: true,
  maxSpeedKmph: 30,
  hasWatering: true,
  slots: [],
}));

export const INITIAL_PLATFORMS_GZB: PlatformInfo[] = Array.from({ length: 6 }, (_, i) => ({
  platformNumber: i + 1,
  lengthMeters: 580,
  isElectrified: true,
  maxSpeedKmph: 30,
  hasWatering: false,
  slots: [],
}));
