import {
  Station,
  StationCode,
  Train,
  PlatformInfo,
  PlatformSlot,
  CrewMember,
  Advisory,
  MaintenanceBlock,
  AuditEntry,
} from './types';
import { STATIONS, INITIAL_PLATFORMS_CNB, INITIAL_PLATFORMS_NDLS, INITIAL_PLATFORMS_GZB } from './stations';
import { buildInitialTrains } from './trains';
import { INITIAL_CREW } from './crew';
import { INITIAL_ADVISORIES } from './advisories';
import { INITIAL_MAINTENANCE } from './maintenance';
import { INITIAL_AUDIT_LOGS } from './audit';
import { F14_PROOF_METRICS, HORIZON_MAE_DATA, METHODOLOGY_NOTES } from './model';

// Build initial platform slots for CNB
function buildPlatformSlots(trains: Train[]): PlatformInfo[] {
  const platforms = JSON.parse(JSON.stringify(INITIAL_PLATFORMS_CNB)) as PlatformInfo[];

  trains.slice(0, 15).forEach((t, idx) => {
    const pfIndex = (t.platform - 1) % platforms.length;
    const arrParts = t.predictedArrival.split(':').map(Number);
    const depParts = t.predictedDeparture.split(':').map(Number);
    const startMinutes = arrParts[0] * 60 + arrParts[1];
    let endMinutes = depParts[0] * 60 + depParts[1];
    if (endMinutes <= startMinutes) {
      endMinutes = startMinutes + 15; // default 15 min stop
    }

    // Mark deliberate conflict on PF3 between 12034 and 12301 for the demo
    const isConflict = t.platform === 3 && (t.number === '12034' || t.number === '12301');

    const slot: PlatformSlot = {
      id: `SLOT-${t.number}-${t.platform}`,
      trainNo: t.number,
      trainName: t.name,
      arrivalTime: t.predictedArrival,
      departureTime: t.predictedDeparture,
      startMinutes,
      endMinutes,
      status: isConflict ? 'conflict' : 'scheduled',
      isConflict,
      conflictWithTrainNo: isConflict ? (t.number === '12034' ? '12301' : '12034') : undefined,
      platform: t.platform,
    };

    platforms[pfIndex].slots.push(slot);
  });

  return platforms;
}

class MockDataStore {
  private activeStation: StationCode = 'CNB';
  private stations: Record<string, Station> = { ...STATIONS };
  private trains: Train[] = buildInitialTrains();
  private platformsCNB: PlatformInfo[] = [];
  private platformsNDLS: PlatformInfo[] = INITIAL_PLATFORMS_NDLS;
  private platformsGZB: PlatformInfo[] = INITIAL_PLATFORMS_GZB;
  private crew: CrewMember[] = [...INITIAL_CREW];
  private advisories: Advisory[] = [...INITIAL_ADVISORIES];
  private maintenance: MaintenanceBlock[] = [...INITIAL_MAINTENANCE];
  private auditLogs: AuditEntry[] = [...INITIAL_AUDIT_LOGS];
  private lastUpdated: Date = new Date();
  private listeners: Set<() => void> = new Set();
  private timer: number | null = null;
  private tickCount: number = 0;

  constructor() {
    this.platformsCNB = buildPlatformSlots(this.trains);
    this.startLiveTick();
  }

  public subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notify(): void {
    this.listeners.forEach(cb => cb());
  }

  public getActiveStation(): StationCode {
    return this.activeStation;
  }

  public setActiveStation(code: StationCode, actor: string = 'Station Master'): void {
    if (this.stations[code]) {
      this.activeStation = code;
      this.addAuditEntry({
        eventType: 'station_switch',
        zone: `${this.stations[code].zone} / ${code}`,
        action: `Switched Operating Context to ${this.stations[code].name}`,
        actor,
        details: `Active console station changed to ${this.stations[code].fullName}.`,
      });
      this.notify();
    }
  }

  public getStation(code: StationCode = this.activeStation): Station {
    const station = { ...this.stations[code] };
    station.platformConflictsCount = this.advisories.filter(a => a.stationCode === code && a.status === 'pending' && a.priority === 'danger').length;
    station.pendingAdvisoriesCount = this.advisories.filter(a => a.stationCode === code && a.status === 'pending').length;
    station.crewWarningsCount = this.crew.filter(c => c.status !== 'ok').length;
    return station;
  }

  public getTrains(): Train[] {
    return [...this.trains];
  }

  public getTrain(number: string): Train | undefined {
    return this.trains.find(t => t.number === number);
  }

  public getPlatforms(code: StationCode = this.activeStation): PlatformInfo[] {
    if (code === 'NDLS') return this.platformsNDLS;
    if (code === 'GZB') return this.platformsGZB;
    return this.platformsCNB;
  }

  public getCrew(): CrewMember[] {
    return [...this.crew];
  }

  public getAdvisories(): Advisory[] {
    return [...this.advisories];
  }

  public getMaintenance(): MaintenanceBlock[] {
    return [...this.maintenance];
  }

  public getAuditLogs(): AuditEntry[] {
    return [...this.auditLogs];
  }

  public getLastUpdated(): Date {
    return this.lastUpdated;
  }

  public getModelProof() {
    return {
      f14Metrics: F14_PROOF_METRICS,
      horizonMae: HORIZON_MAE_DATA,
      methodologyNotes: METHODOLOGY_NOTES,
    };
  }

  // --- Mutations ---

  public acceptAdvisory(id: string, reason: string = 'Accepted per recommendation', actor: string = 'Station Master'): boolean {
    const advIndex = this.advisories.findIndex(a => a.id === id);
    if (advIndex === -1) return false;

    const adv = this.advisories[advIndex];
    adv.status = 'accepted';
    adv.triageReason = reason;

    // Apply mutation to train if platform change
    if (adv.suggestedPlatform && adv.trainNo) {
      const train = this.trains.find(t => t.number === adv.trainNo);
      if (train) {
        const oldPf = train.platform;
        train.platform = adv.suggestedPlatform;
        train.assignedPlatform = adv.suggestedPlatform;

        // Update platform slots
        this.platformsCNB.forEach(p => {
          p.slots = p.slots.filter(s => s.trainNo !== adv.trainNo);
          if (p.platformNumber === adv.suggestedPlatform) {
            p.slots.push({
              id: `SLOT-${train.number}-${adv.suggestedPlatform}`,
              trainNo: train.number,
              trainName: train.name,
              arrivalTime: train.predictedArrival,
              departureTime: train.predictedDeparture,
              startMinutes: parseInt(train.predictedArrival.split(':')[0], 10) * 60 + parseInt(train.predictedArrival.split(':')[1], 10),
              endMinutes: parseInt(train.predictedDeparture.split(':')[0], 10) * 60 + parseInt(train.predictedDeparture.split(':')[1], 10) + 10,
              status: 'reassigned',
              isConflict: false,
              platform: adv.suggestedPlatform,
            });
          }
        });

        // Resolve conflict status on PF3
        this.platformsCNB.forEach(p => {
          p.slots.forEach(s => {
            if (s.conflictWithTrainNo === adv.trainNo) {
              s.isConflict = false;
              s.status = 'scheduled';
              s.conflictWithTrainNo = undefined;
            }
          });
        });

        this.addAuditEntry({
          eventType: 'advisory_ack',
          trainNo: adv.trainNo,
          zone: `${this.stations[adv.stationCode]?.zone || 'NCR'} / ${adv.stationCode}`,
          action: `Advisory ${adv.code} Accepted: Reassigned PF${oldPf} → PF${adv.suggestedPlatform}`,
          actor,
          details: `Reason: ${reason}. Expected delay savings: ${adv.simulatedImpact.delaySavingsMinutes}m. Platform conflict eliminated.`,
          payload: { advisoryId: id, oldPlatform: oldPf, newPlatform: adv.suggestedPlatform },
        });
      }
    } else {
      this.addAuditEntry({
        eventType: 'advisory_ack',
        trainNo: adv.trainNo,
        zone: `${this.stations[adv.stationCode]?.zone || 'NCR'} / ${adv.stationCode}`,
        action: `Advisory ${adv.code} Accepted: ${adv.title}`,
        actor,
        details: `Reason: ${reason}. Action taken: ${adv.recommendedAction}`,
        payload: { advisoryId: id, impact: adv.simulatedImpact },
      });
    }

    this.lastUpdated = new Date();
    this.notify();
    return true;
  }

  public dismissAdvisory(id: string, reason: string = 'Manual override by dispatcher', actor: string = 'Station Master'): boolean {
    const advIndex = this.advisories.findIndex(a => a.id === id);
    if (advIndex === -1) return false;

    const adv = this.advisories[advIndex];
    adv.status = 'dismissed';
    adv.triageReason = reason;

    this.addAuditEntry({
      eventType: 'advisory_dismiss',
      trainNo: adv.trainNo,
      zone: `${this.stations[adv.stationCode]?.zone || 'NCR'} / ${adv.stationCode}`,
      action: `Advisory ${adv.code} Dismissed: ${adv.title}`,
      actor,
      details: `Dismissal Rationale: ${reason}. Current plan retained under dispatcher discretion.`,
      payload: { advisoryId: id },
    });

    this.lastUpdated = new Date();
    this.notify();
    return true;
  }

  public requestCrewRelief(crewId: string, actor: string = 'Crew Supervisor'): boolean {
    const member = this.crew.find(c => c.id === crewId);
    if (!member) return false;

    member.reliefRequested = true;
    member.status = 'ok';

    this.addAuditEntry({
      eventType: 'crew_relief',
      trainNo: member.trainNo,
      zone: 'NCR / CNB Crew Running Room',
      action: `Relief Crew Dispatched for ${member.name} (${member.id})`,
      actor,
      details: `Relief crew arranged at ${member.reliefStation} for train ${member.trainNo} ${member.trainName}. Breach risk averted.`,
      payload: { crewId, pilot: member.name, trainNo: member.trainNo },
    });

    this.lastUpdated = new Date();
    this.notify();
    return true;
  }

  public reoptimizePlatforms(stationCode: StationCode = this.activeStation, actor: string = 'System Re-optimizer'): { resolvedCount: number; swapsCount: number } {
    let resolvedCount = 0;
    let swapsCount = 0;

    // Find and resolve pending platform conflicts
    this.advisories.forEach(a => {
      if (a.stationCode === stationCode && a.status === 'pending' && a.suggestedPlatform) {
        this.acceptAdvisory(a.id, 'Automated one-click re-optimization MILP solver', actor);
        resolvedCount++;
        swapsCount += 2;
      }
    });

    if (resolvedCount === 0) {
      swapsCount = 1;
      resolvedCount = 1;
    }

    this.addAuditEntry({
      eventType: 'platform_reopt',
      zone: `${this.stations[stationCode].zone} / ${stationCode}`,
      action: `Platform Plan Re-Optimized (<1.5s)`,
      actor,
      details: `Solved platform conflict model in 1.38s. ${swapsCount} platform assignments modified to clear 0 headway conflicts.`,
      payload: { resolvedCount, swapsCount, latencyMs: 1380 },
    });

    this.lastUpdated = new Date();
    this.notify();
    return { resolvedCount, swapsCount };
  }

  private addAuditEntry(entry: Omit<AuditEntry, 'id' | 'timestamp' | 'referenceHash'> & { id?: string; timestamp?: string; referenceHash?: string }): void {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-IN', { hour12: false });
    const hash = `0x${Math.floor(Math.random() * 0xffffffffffff).toString(16).padStart(12, '0')}`;
    const newEntry: AuditEntry = {
      id: entry.id || `AUD-${now.toISOString().slice(0, 10).replace(/-/g, '')}-${(this.auditLogs.length + 1).toString().padStart(3, '0')}`,
      timestamp: entry.timestamp || timeStr,
      eventType: entry.eventType,
      trainNo: entry.trainNo,
      zone: entry.zone,
      action: entry.action,
      actor: entry.actor,
      details: entry.details,
      referenceHash: entry.referenceHash || hash,
      payload: entry.payload,
    };
    this.auditLogs.unshift(newEntry);
  }

  // --- Live Tick Engine (5s interval) ---

  private startLiveTick(): void {
    if (typeof window === 'undefined') return;

    this.timer = window.setInterval(() => {
      this.tickCount++;
      this.lastUpdated = new Date();

      // Realistic small jitter: pick 1-2 random trains and drift ETA ±1-2 min
      if (this.trains.length > 0) {
        const randIndex = Math.floor(Math.random() * Math.min(10, this.trains.length));
        const train = this.trains[randIndex];
        const delta = Math.random() > 0.6 ? 1 : Math.random() > 0.3 ? -1 : 0;

        if (delta !== 0) {
          train.delayMinutes = Math.max(0, train.delayMinutes + delta);
          train.status = train.delayMinutes > 20 ? 'critical' : train.delayMinutes > 5 ? 'delayed' : 'on_time';
          train.updatedAt = new Date().toISOString();
        }
      }

      // Spontaneous new advisory or event every ~25 ticks (~125 seconds)
      if (this.tickCount % 25 === 0 && this.advisories.filter(a => a.status === 'pending').length < 6) {
        const randTrain = this.trains[Math.floor(Math.random() * 8)];
        const newAdvId = `ADV-CNB-${Math.floor(1000 + Math.random() * 9000)}`;
        const newAdv: Advisory = {
          id: newAdvId,
          code: `ADV-${newAdvId.split('-')[2]}`,
          priority: 'warn',
          title: `Outer Signal Deceleration Warning: Train ${randTrain.number}`,
          trainNo: randTrain.number,
          trainName: randTrain.name,
          stationCode: 'CNB',
          suggestedPlatform: (randTrain.platform % 10) + 1,
          rationale: `Section headway between Panki and CNB Outer compressing below safety threshold (3.8 min).`,
          recommendedAction: `Regulate approach speed to 40 km/h and prepare routing for alternative platform ${((randTrain.platform % 10) + 1)}.`,
          simulatedImpact: {
            delaySavingsMinutes: 12,
            conflictResolved: true,
            cascadePreventedCount: 2,
          },
          status: 'pending',
          humanAckRequired: true,
          createdAt: new Date().toLocaleTimeString('en-IN', { hour12: false }),
          expiresAt: new Date(Date.now() + 15 * 60000).toLocaleTimeString('en-IN', { hour12: false }),
        };
        this.advisories.unshift(newAdv);
        this.addAuditEntry({
          eventType: 'system_tick',
          trainNo: randTrain.number,
          zone: 'NCR / CNB Approach',
          action: `Automated Advisory Issued: ${newAdv.title}`,
          actor: 'SYS (RailTwin-X Engine)',
          details: `Dynamic spatial conflict engine detected headway compression. Advisory ${newAdv.code} generated.`,
          payload: { advisoryId: newAdvId },
        });
      }

      this.notify();
    }, 5000);
  }

  public destroy(): void {
    if (this.timer !== null) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }
}

export const mockStore = new MockDataStore();
