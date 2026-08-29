import { mockStore } from './store';
import { StationCode, Train, Station, PlatformInfo, CrewMember, Advisory, MaintenanceBlock, AuditEntry } from './types';

// Simulated delay helper
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const api = {
  // Station State
  async getStation(code?: StationCode): Promise<Station> {
    await delay(30);
    return mockStore.getStation(code);
  },

  async switchStation(code: StationCode, actor?: string): Promise<Station> {
    await delay(200);
    mockStore.setActiveStation(code, actor);
    return mockStore.getStation(code);
  },

  // Trains
  async getTrains(): Promise<Train[]> {
    await delay(40);
    return mockStore.getTrains();
  },

  async getTrain(number: string): Promise<Train | null> {
    await delay(50);
    return mockStore.getTrain(number) || null;
  },

  // Platforms / Gantt
  async getPlatforms(code?: StationCode): Promise<PlatformInfo[]> {
    await delay(50);
    return mockStore.getPlatforms(code);
  },

  async reoptimizePlatforms(stationCode?: StationCode): Promise<{ resolvedCount: number; swapsCount: number }> {
    await delay(600); // 600ms realistic solver latency per §10
    return mockStore.reoptimizePlatforms(stationCode);
  },

  // Advisories
  async getAdvisories(): Promise<Advisory[]> {
    await delay(40);
    return mockStore.getAdvisories();
  },

  async acceptAdvisory(id: string, reason?: string, actor?: string): Promise<boolean> {
    await delay(450);
    return mockStore.acceptAdvisory(id, reason, actor);
  },

  async dismissAdvisory(id: string, reason?: string, actor?: string): Promise<boolean> {
    await delay(400);
    return mockStore.dismissAdvisory(id, reason, actor);
  },

  // Crew
  async getCrew(): Promise<CrewMember[]> {
    await delay(40);
    return mockStore.getCrew();
  },

  async requestCrewRelief(crewId: string, actor?: string): Promise<boolean> {
    await delay(500);
    return mockStore.requestCrewRelief(crewId, actor);
  },

  // Maintenance
  async getMaintenance(): Promise<MaintenanceBlock[]> {
    await delay(40);
    return mockStore.getMaintenance();
  },

  // Audit Logs
  async getAuditLogs(): Promise<AuditEntry[]> {
    await delay(40);
    return mockStore.getAuditLogs();
  },

  // Model Proof
  async getModelProof() {
    await delay(30);
    return mockStore.getModelProof();
  },

  // Access Request Form
  async requestAccess(data: { stationCode: string; name: string; email: string; organisation: string }): Promise<{ success: boolean; id: string }> {
    await delay(600);
    return {
      success: true,
      id: `REQ-${Math.floor(100000 + Math.random() * 900000)}`,
    };
  },
};
