import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { CookieBanner } from '@/components/shell/CookieBanner';

// Public Pages
import { LandingPage } from '@/pages/landing/LandingPage';
import { LoginPage } from '@/pages/auth/LoginPage';
import { KioskPage } from '@/pages/public/KioskPage';
import { PrivacyPage } from '@/pages/public/PrivacyPage';
import { TermsPage } from '@/pages/public/TermsPage';
import { ThanksPage } from '@/pages/public/ThanksPage';
import { NotFoundPage } from '@/pages/public/NotFoundPage';

// Core Dashboard Pages (Lazy loaded)
const OverviewPage = lazy(() => import('@/pages/dashboard/OverviewPage').then(m => ({ default: m.OverviewPage })));
const LiveMapPage = lazy(() => import('@/pages/dashboard/LiveMapPage').then(m => ({ default: m.LiveMapPage })));
const GanttPage = lazy(() => import('@/pages/dashboard/GanttPage').then(m => ({ default: m.GanttPage })));
const TrainsPage = lazy(() => import('@/pages/dashboard/TrainsPage').then(m => ({ default: m.TrainsPage })));
const TrainDetailPage = lazy(() => import('@/pages/dashboard/TrainDetailPage').then(m => ({ default: m.TrainDetailPage })));
const AdvisoriesPage = lazy(() => import('@/pages/dashboard/AdvisoriesPage').then(m => ({ default: m.AdvisoriesPage })));
const CrewPage = lazy(() => import('@/pages/dashboard/CrewPage').then(m => ({ default: m.CrewPage })));
const MaintenancePage = lazy(() => import('@/pages/dashboard/MaintenancePage').then(m => ({ default: m.MaintenancePage })));
const AuditPage = lazy(() => import('@/pages/dashboard/AuditPage').then(m => ({ default: m.AuditPage })));
const ModelPage = lazy(() => import('@/pages/dashboard/ModelPage').then(m => ({ default: m.ModelPage })));

// Core Operational & Network Pages (PS 26028)
const TimetablePage = lazy(() => import('@/pages/dashboard/ops/TimetablePage').then(m => ({ default: m.TimetablePage })));
const BlockSectionsPage = lazy(() => import('@/pages/dashboard/ops/BlockSectionsPage').then(m => ({ default: m.BlockSectionsPage })));
const CorridorMapPage = lazy(() => import('@/pages/dashboard/network/CorridorMapPage').then(m => ({ default: m.CorridorMapPage })));
const YardDiagramPage = lazy(() => import('@/pages/dashboard/network/YardDiagramPage').then(m => ({ default: m.YardDiagramPage })));

// Safety & Coordination Pages (TSR & DFC Headway)
const TSRRegistryPage = lazy(() => import('@/pages/dashboard/safety/TSRRegistryPage').then(m => ({ default: m.TSRRegistryPage })));
const IncidentsPage = lazy(() => import('@/pages/dashboard/safety/IncidentsPage').then(m => ({ default: m.IncidentsPage })));
const CorridorHandoffPage = lazy(() => import('@/pages/dashboard/coord/CorridorHandoffPage').then(m => ({ default: m.CorridorHandoffPage })));
const DFCPrecedencePage = lazy(() => import('@/pages/dashboard/coord/DFCPrecedencePage').then(m => ({ default: m.DFCPrecedencePage })));

function RouteFallback() {
  return (
    <div className="p-8 font-mono text-xs text-[#9A9DA3] flex items-center gap-2">
      <span className="w-2 h-2 rounded-full bg-[#FFB224] animate-pulse" />
      <span>Loading operational module...</span>
    </div>
  );
}

export function App() {
  return (
    <>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/kiosk" element={<KioskPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/thanks" element={<ThanksPage />} />

        {/* Private Dashboard Shell (AuthGuard Protected) */}
        <Route
          path="/dashboard"
          element={
            <AuthGuard>
              <DashboardLayout />
            </AuthGuard>
          }
        >
          {/* Core Overview & Real-Time Intelligence */}
          <Route index element={<Suspense fallback={<RouteFallback />}><OverviewPage /></Suspense>} />
          <Route path="live-map" element={<Suspense fallback={<RouteFallback />}><LiveMapPage /></Suspense>} />
          <Route path="map" element={<Suspense fallback={<RouteFallback />}><LiveMapPage /></Suspense>} />

          {/* Trains & Causal Delay Autopsy */}
          <Route path="trains" element={<Suspense fallback={<RouteFallback />}><TrainsPage /></Suspense>} />
          <Route path="trains/:trainNo" element={<Suspense fallback={<RouteFallback />}><TrainDetailPage /></Suspense>} />

          {/* Operations & Platform Re-Optimization */}
          <Route path="gantt" element={<Suspense fallback={<RouteFallback />}><GanttPage /></Suspense>} />
          <Route path="advisories" element={<Suspense fallback={<RouteFallback />}><AdvisoriesPage /></Suspense>} />
          <Route path="timetable" element={<Suspense fallback={<RouteFallback />}><TimetablePage /></Suspense>} />
          <Route path="blocks" element={<Suspense fallback={<RouteFallback />}><BlockSectionsPage /></Suspense>} />

          {/* Network Topology & Corridor GIS */}
          <Route path="corridor-gis" element={<Suspense fallback={<RouteFallback />}><CorridorMapPage /></Suspense>} />
          <Route path="yard-map" element={<Suspense fallback={<RouteFallback />}><YardDiagramPage /></Suspense>} />

          {/* Safety & Speed Restrictions (TSR) */}
          <Route path="safety/tsr" element={<Suspense fallback={<RouteFallback />}><TSRRegistryPage /></Suspense>} />
          <Route path="safety/incidents" element={<Suspense fallback={<RouteFallback />}><IncidentsPage /></Suspense>} />

          {/* Workforce & Maintenance */}
          <Route path="crew" element={<Suspense fallback={<RouteFallback />}><CrewPage /></Suspense>} />
          <Route path="maintenance" element={<Suspense fallback={<RouteFallback />}><MaintenancePage /></Suspense>} />

          {/* Corridor Handoff & DFC Precedence */}
          <Route path="corridor-coordination" element={<Suspense fallback={<RouteFallback />}><CorridorHandoffPage /></Suspense>} />
          <Route path="dfc-coordination" element={<Suspense fallback={<RouteFallback />}><DFCPrecedencePage /></Suspense>} />

          {/* Model Proof & Tamper-Evident Ledger */}
          <Route path="audit" element={<Suspense fallback={<RouteFallback />}><AuditPage /></Suspense>} />
          <Route path="model" element={<Suspense fallback={<RouteFallback />}><ModelPage /></Suspense>} />
        </Route>

        {/* 404 Catch-All */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>

      {/* Global Cookieless Consent Banner */}
      <CookieBanner />
    </>
  );
}
