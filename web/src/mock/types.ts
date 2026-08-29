export type StationCode = 'CNB' | 'NDLS' | 'GZB';

export interface Station {
  code: StationCode;
  name: string;
  fullName: string;
  division: string;
  zone: string;
  platformsCount: number;
  activeTrainsCount: number;
  platformConflictsCount: number;
  pendingAdvisoriesCount: number;
  crewWarningsCount: number;
  corridorAvgDelayMinutes: number;
}

export interface PlatformSlot {
  id: string;
  trainNo: string;
  trainName: string;
  arrivalTime: string; // HH:MM
  departureTime: string; // HH:MM
  startMinutes: number; // minutes from 00:00 for gantt
  endMinutes: number;
  status: 'scheduled' | 'occupied' | 'conflict' | 'reassigned';
  isConflict: boolean;
  conflictWithTrainNo?: string;
  platform: number;
}

export interface PlatformInfo {
  platformNumber: number;
  lengthMeters: number;
  isElectrified: boolean;
  maxSpeedKmph: number;
  hasWatering: boolean;
  slots: PlatformSlot[];
}

export interface ETAConfidenceBand {
  p10: string; // Optimistic HH:MM
  p50: string; // Likely HH:MM
  p90: string; // Pessimistic HH:MM
  spreadMinutes: number;
}

export interface JourneyStop {
  seq: number;
  stationCode: string;
  stationName: string;
  schedArrival: string;
  schedDeparture: string;
  actualArrival?: string;
  actualDeparture?: string;
  predArrival?: string;
  predDeparture?: string;
  delayMinutes: number;
  status: 'passed' | 'current' | 'upcoming';
  distanceKm: number;
}

export interface DelayAutopsyItem {
  cause: string;
  minutes: number;
  category: 'Signaling' | 'Precedence' | 'Speed Restriction' | 'Turnaround' | 'Weather/Fog' | 'Terminal Congestion';
  description: string;
  percentage: number;
}

export type TrainType =
  | 'Vande Bharat'
  | 'Rajdhani Express'
  | 'Shatabdi Express'
  | 'Duronto Express'
  | 'Superfast'
  | 'Mail / Express'
  | 'DFC Freight';

export interface Train {
  number: string;
  name: string;
  type: TrainType;
  origin: string;
  destination: string;
  currentStation: string;
  nextStation: string;
  routePosition: string; // e.g. "Approaching Outer Signal (KM 1014.2)"
  scheduledArrival: string;
  scheduledDeparture: string;
  predictedArrival: string;
  predictedDeparture: string;
  etaBand: ETAConfidenceBand;
  delayMinutes: number;
  platform: number;
  assignedPlatform: number;
  speedKmph: number;
  priority: number; // 1 = highest
  rakeId: string;
  status: 'on_time' | 'delayed' | 'critical';
  journey: JourneyStop[];
  delayAutopsy: DelayAutopsyItem[];
  updatedAt: string;
}

export interface CrewMember {
  id: string;
  name: string;
  designation: 'Loco Pilot (Mail/Exp)' | 'Loco Pilot (Passenger)' | 'Loco Pilot (Goods)' | 'Assistant Loco Pilot' | 'Train Manager (Guard)';
  trainNo: string;
  trainName: string;
  signOnStation: string;
  signOnTime: string;
  dutyHoursSoFar: number;
  maxAllowedHours: number; // Standard 10.0h, max 12.0h
  projectedTotalHours: number;
  remainingHours: number;
  status: 'ok' | 'advisory' | 'critical'; // critical < 2h, advisory 2-4h
  reliefStation: string;
  reliefRequested: boolean;
  phone: string;
}

export interface Advisory {
  id: string;
  code: string;
  priority: 'danger' | 'warn' | 'neutral';
  title: string;
  trainNo: string;
  trainName: string;
  stationCode: StationCode;
  platform?: number;
  suggestedPlatform?: number;
  rationale: string;
  recommendedAction: string;
  simulatedImpact: {
    delaySavingsMinutes: number;
    conflictResolved: boolean;
    cascadePreventedCount: number;
  };
  status: 'pending' | 'accepted' | 'dismissed';
  humanAckRequired: boolean;
  triageReason?: string;
  createdAt: string;
  expiresAt: string;
}

export interface MaintenanceBlock {
  id: string;
  blockRef: string;
  section: string;
  trackId: 'UP MAIN' | 'DOWN MAIN' | 'UP LOOP' | 'DOWN LOOP' | 'DFC EASTERN';
  speedRestrictionKmph: number;
  workType: 'Track Tamping' | 'OHE 25kV Inspection' | 'Deep Screening' | 'Bridge Girder Maintenance' | 'Signaling Interlock Overhaul';
  startTime: string;
  endTime: string;
  durationHours: number;
  affectedTrains: string[];
  advisoryNote: string;
  status: 'active' | 'upcoming' | 'completed';
}

export interface AuditEntry {
  id: string;
  timestamp: string; // ISO / HH:MM:SS
  eventType: 'advisory_ack' | 'advisory_dismiss' | 'platform_reopt' | 'crew_relief' | 'speed_regulation' | 'station_switch' | 'system_tick';
  trainNo?: string;
  zone: string;
  action: string;
  actor: string;
  details: string;
  referenceHash: string;
  payload?: Record<string, unknown>;
}

export interface F14Metric {
  metric: string;
  baseline1: string; // Static / Scheduled
  baseline2: string; // NTES Constant Velocity
  railtwin: string; // RailTwin-X Champion
  improvement: string;
  targetAchieved: boolean;
}

export interface HorizonMAE {
  horizon: string;
  baseline1: number;
  baseline2: number;
  railtwin: number;
}

export interface UserSession {
  user: {
    id: string;
    username?: string;
    email: string;
    name: string;
    role: string;
    roleName?: string;
    station: StationCode;
    stationName: string;
    token?: string;
  };
  expiresAt: number; // Unix timestamp ms
}

