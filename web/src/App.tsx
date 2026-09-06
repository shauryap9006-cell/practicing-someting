import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConnectionProvider } from './lib/api';
import { AppShell } from './shell';
import { LoadingState } from './primitives';

// Lazy load all 6 surfaces + Landing page
const LandingPage = lazy(() =>
  import('./landing/LandingPage').then((m) => ({ default: m.LandingPage }))
);
const TrainSearchPage = lazy(() =>
  import('./pages/TrainSearchPage').then((m) => ({ default: m.TrainSearchPage }))
);
const TrainPage = lazy(() =>
  import('./pages/TrainPage').then((m) => ({ default: m.TrainPage }))
);
const NetworkPage = lazy(() =>
  import('./pages/NetworkPage').then((m) => ({ default: m.NetworkPage }))
);
const ComparePage = lazy(() =>
  import('./pages/ComparePage').then((m) => ({ default: m.ComparePage }))
);
const ProofPage = lazy(() =>
  import('./pages/ProofPage').then((m) => ({ default: m.ProofPage }))
);
const KioskPage = lazy(() =>
  import('./pages/KioskPage').then((m) => ({ default: m.KioskPage }))
);
const NotFoundPage = lazy(() =>
  import('./pages/NotFoundPage').then((m) => ({ default: m.NotFoundPage }))
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConnectionProvider>
        <BrowserRouter>
          <Suspense
            fallback={
              <div className="min-h-screen bg-paper flex items-center justify-center p-6">
                <LoadingState rows={3} message="Initializing RailTwin-X v4..." />
              </div>
            }
          >
            <Routes>
              {/* Fullscreen Surfaces (Landing 3D & Station PIDS) */}
              <Route path="/" element={<LandingPage />} />
              <Route path="/kiosk" element={<KioskPage />} />

              {/* Standard AppShell Surfaces (Tracker, Twin, Lab, Proof) */}
              <Route
                path="/t"
                element={
                  <AppShell>
                    <TrainSearchPage />
                  </AppShell>
                }
              />
              <Route
                path="/t/:trainNo"
                element={
                  <AppShell>
                    <TrainPage />
                  </AppShell>
                }
              />
              <Route
                path="/network"
                element={
                  <AppShell>
                    <NetworkPage />
                  </AppShell>
                }
              />
              <Route
                path="/compare"
                element={
                  <AppShell>
                    <ComparePage />
                  </AppShell>
                }
              />
              <Route
                path="/proof"
                element={
                  <AppShell>
                    <ProofPage />
                  </AppShell>
                }
              />

              {/* Backward-Compatibility Redirects */}
              <Route path="/track" element={<Navigate to="/t" replace />} />
              <Route path="/track/:trainNo" element={<Navigate to="/t/:trainNo" replace />} />
              <Route path="/corridor" element={<Navigate to="/network" replace />} />
              <Route path="/foresight" element={<Navigate to="/compare" replace />} />
              <Route path="/ledger" element={<Navigate to="/proof" replace />} />
              <Route path="/pids" element={<Navigate to="/kiosk" replace />} />

              {/* 404 Route */}
              <Route
                path="*"
                element={
                  <AppShell>
                    <NotFoundPage />
                  </AppShell>
                }
              />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </ConnectionProvider>
    </QueryClientProvider>
  );
}
