/**
 * RailTwin-X Canonical TanStack Query Keys & Invalidation Resource Graph (F37).
 *
 * Provides typed, structured query keys and invalidation mappings so mutations
 * reliably refresh active views across Platform Gantt, Live Board, Train Journey,
 * and KPI dashboards.
 */

export const queryKeys = {
  station: (code?: string) => ['station', code || 'NDLS'] as const,
  board: (stationCode: string, date?: string, kind?: string) =>
    ['board', stationCode, date || 'today', kind || 'all'] as const,
  train: (trainNo: string) => ['train', trainNo] as const,
  trainJourney: (trainNo: string) => ['train', trainNo, 'journey'] as const,
  trainAutopsy: (trainNo: string) => ['train', trainNo, 'autopsy'] as const,
  platforms: (stationCode?: string) => ['platforms', stationCode || 'NDLS'] as const,
  advisories: () => ['advisories'] as const,
  crew: () => ['crew'] as const,
  maintenance: () => ['maintenance'] as const,
  audit: () => ['audit'] as const,
  modelInfo: () => ['model', 'info'] as const,
  modelProof: () => ['model', 'proof'] as const,
  kpi: () => ['kpi'] as const,
  corridorTopology: () => ['corridor', 'topology'] as const,
  tsr: (stationCode?: string) => ['safety', 'tsr', stationCode || 'NDLS'] as const,
  incidents: (stationCode?: string) => ['safety', 'incidents', stationCode || 'NDLS'] as const,
  workOrders: (stationCode?: string) => ['infra', 'work-orders', stationCode || 'NDLS'] as const,
};

/**
 * Mutation Invalidation Graph: Defines which query keys are invalidated upon specific operational mutations.
 */
export const mutationInvalidationMap = {
  setIn: (stationCode: string, trainNo: string) => [
    queryKeys.board(stationCode),
    queryKeys.platforms(stationCode),
    queryKeys.trainJourney(trainNo),
    queryKeys.kpi(),
  ],
  setOut: (stationCode: string, trainNo: string) => [
    queryKeys.board(stationCode),
    queryKeys.platforms(stationCode),
    queryKeys.trainJourney(trainNo),
    queryKeys.kpi(),
  ],
  reoptimizePlatforms: (stationCode: string) => [
    queryKeys.platforms(stationCode),
    queryKeys.board(stationCode),
    queryKeys.advisories(),
  ],
  acceptAdvisory: (stationCode?: string) => [
    queryKeys.advisories(),
    queryKeys.board(stationCode || 'NDLS'),
    queryKeys.platforms(stationCode || 'NDLS'),
  ],
  createTSR: (stationCode?: string) => [
    queryKeys.tsr(stationCode),
    queryKeys.board(stationCode || 'NDLS'),
    queryKeys.corridorTopology(),
  ],
  liftTSR: (stationCode?: string) => [
    queryKeys.tsr(stationCode),
    queryKeys.board(stationCode || 'NDLS'),
    queryKeys.corridorTopology(),
  ],
};
