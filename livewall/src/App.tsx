import React, { useState, useMemo } from 'react';
import { useLiveFeed } from './lib/feed';
import { NATIONAL_CORRIDORS, getCorridorById } from './lib/corridors';
import { HeaderBar } from './components/HeaderBar';
import { CorridorSelector } from './components/CorridorSelector';
import { CorridorMap } from './components/CorridorMap';
import { StationMasterView } from './components/StationMasterView';
import { CongestionBar } from './components/CongestionBar';
import { EventTicker } from './components/EventTicker';
import { DevPanel } from './components/DevPanel';
import { TrainInspector } from './components/TrainInspector';

export const App: React.FC = () => {
  const {
    positions,
    clock,
    network,
    congestion,
    board,
    events,
    allStations,
    selectedStationCode,
    setSelectedStationCode,
    platformStates,
    connection,
    isStale,
  } = useLiveFeed();

  const [selectedTrainNo, setSelectedTrainNo] = useState<string | null>(null);
  const [activeCorridorId, setActiveCorridorId] = useState<string>('NDLS_LKO');

  // Active Corridor Metadata
  const activeCorridor = useMemo(() => {
    return getCorridorById(activeCorridorId) || NATIONAL_CORRIDORS[0];
  }, [activeCorridorId]);

  // Handle switching corridor
  const handleSelectCorridor = (corridorId: string) => {
    setActiveCorridorId(corridorId);
    const corr = getCorridorById(corridorId);
    if (corr && corr.stations.length > 0) {
      setSelectedStationCode(corr.stations[0].code);
    }
  };

  // Active Station metadata for the Station Master view
  const activeStation = useMemo(() => {
    if (selectedStationCode) {
      // 1. First check in active corridor stations
      const inCorridor = activeCorridor.stations.find(
        (s) => s.code.toUpperCase() === selectedStationCode.toUpperCase()
      );
      if (inCorridor) return inCorridor;

      // 2. Then check in allStations
      if (allStations && allStations.length > 0) {
        const found = allStations.find(
          (s) => s.code.toUpperCase() === selectedStationCode.toUpperCase()
        );
        if (found) return found;
      }
    }

    // Default to the first station on the active corridor
    return (
      activeCorridor.stations[0] || {
        code: 'NDLS',
        name: 'New Delhi',
        platforms: 16,
        is_junction: 1,
        lat: 28.6143,
        lon: 77.2188,
      }
    );
  }, [selectedStationCode, activeCorridor, allStations]);

  const containerClass = `wall-container corridor-mode ${
    connection === 'offline' ? 'offline' : isStale ? 'stale' : ''
  }`;

  return (
    <>
      {/* Telemetry Offline Warning Banner */}
      {connection === 'offline' && (
        <div className="offline-banner">
          [OFFLINE] CORRIDOR TELEMETRY OFFLINE &bull; RECONNECTING TO TWIN STREAM...
        </div>
      )}

      <main className={containerClass}>
        {/* Row 1: HeaderBar (7.5vh) with Universal Search */}
        <HeaderBar
          clock={clock}
          network={network}
          connection={connection}
          isStale={isStale}
          corridorName={activeCorridor.shortName}
          positions={positions}
          stations={allStations.length > 0 ? allStations : activeCorridor.stations}
          onSelectTrain={setSelectedTrainNo}
          onSelectStation={(code) => setSelectedStationCode(code)}
          onSelectCorridor={handleSelectCorridor}
        />

        {/* Row 2: Dedicated Corridor Selection Strip (5.5vh) */}
        <CorridorSelector
          activeCorridorId={activeCorridorId}
          onSelectCorridor={handleSelectCorridor}
          positions={positions}
        />

        {/* Row 3: Linear CTC Corridor Mimic Canvas (34vh) */}
        <CorridorMap
          positions={positions}
          stations={activeCorridor.stations}
          network={network}
          isStale={isStale}
          selectedTrainNo={selectedTrainNo}
          selectedStationCode={activeStation.code}
          onSelectTrain={setSelectedTrainNo}
          onSelectStation={(code) => setSelectedStationCode(code)}
        />

        {/* Row 4: Station Master Deep-Dive (3-Column Operations Deck: 44vh) */}
        <StationMasterView
          station={activeStation}
          corridorStations={activeCorridor.stations}
          allStations={allStations.length > 0 ? allStations : activeCorridor.stations}
          board={board}
          positions={positions}
          platformStates={platformStates}
          network={network}
          onSelectStation={(code) => setSelectedStationCode(code)}
          onSelectTrain={setSelectedTrainNo}
        />

        {/* Row 5: Operational Events & Congestion Radar Bar (9vh) */}
        <div className="bottom-telemetry-strip">
          <EventTicker events={events} />
          <CongestionBar congestion={congestion} />
        </div>

        {/* Selected Train Telemetry Inspector Modal */}
        {selectedTrainNo && (
          <TrainInspector
            trainNo={selectedTrainNo}
            positions={positions}
            network={network}
            stations={allStations.length > 0 ? allStations : activeCorridor.stations}
            onClose={() => setSelectedTrainNo(null)}
            onFocusTrain={(tNo) => setSelectedTrainNo(tNo)}
            onSelectStation={(code) => setSelectedStationCode(code)}
          />
        )}

        {/* Hidden Dev Demo Trigger Panel (Shift+S) */}
        <DevPanel />
      </main>
    </>
  );
};

export default App;

