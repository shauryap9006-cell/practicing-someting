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

// Private Dashboard Pages (Lazy loaded for optimal bundle size)
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

// New v3.0 Operations & Network Pages
const TimetablePage = lazy(() => import('@/pages/dashboard/ops/TimetablePage').then(m => ({ default: m.TimetablePage })));
const BlockSectionsPage = lazy(() => import('@/pages/dashboard/ops/BlockSectionsPage').then(m => ({ default: m.BlockSectionsPage })));
const ShuntingPage = lazy(() => import('@/pages/dashboard/ops/ShuntingPage').then(m => ({ default: m.ShuntingPage })));
const CorridorMapPage = lazy(() => import('@/pages/dashboard/network/CorridorMapPage').then(m => ({ default: m.CorridorMapPage })));
const YardDiagramPage = lazy(() => import('@/pages/dashboard/network/YardDiagramPage').then(m => ({ default: m.YardDiagramPage })));

// New v3.0 Safety Pages
const TSRRegistryPage = lazy(() => import('@/pages/dashboard/safety/TSRRegistryPage').then(m => ({ default: m.TSRRegistryPage })));
const IncidentsPage = lazy(() => import('@/pages/dashboard/safety/IncidentsPage').then(m => ({ default: m.IncidentsPage })));
const SOPRunnerPage = lazy(() => import('@/pages/dashboard/safety/SOPRunnerPage').then(m => ({ default: m.SOPRunnerPage })));
const LCMonitorPage = lazy(() => import('@/pages/dashboard/safety/LCMonitorPage').then(m => ({ default: m.LCMonitorPage })));

// New v3.0 Governance & Admin Pages
const ShiftHandoverPage = lazy(() => import('@/pages/dashboard/gov/ShiftHandoverPage').then(m => ({ default: m.ShiftHandoverPage })));
const AdminUsersPage = lazy(() => import('@/pages/dashboard/gov/AdminUsersPage').then(m => ({ default: m.AdminUsersPage })));
const BackupsIntegrityPage = lazy(() => import('@/pages/dashboard/gov/BackupsIntegrityPage').then(m => ({ default: m.BackupsIntegrityPage })));

// New v3.0 Commercial Pages
const DelayCertificatePage = lazy(() => import('@/pages/dashboard/commercial/DelayCertificatePage').then(m => ({ default: m.DelayCertificatePage })));
const AnnouncementsPage = lazy(() => import('@/pages/dashboard/commercial/AnnouncementsPage').then(m => ({ default: m.AnnouncementsPage })));
const StallsLostFoundPage = lazy(() => import('@/pages/dashboard/commercial/StallsLostFoundPage').then(m => ({ default: m.StallsLostFoundPage })));

// New v3.0 Infrastructure Pages
const AssetsRegistryPage = lazy(() => import('@/pages/dashboard/infra/AssetsRegistryPage').then(m => ({ default: m.AssetsRegistryPage })));
const WorkOrdersPage = lazy(() => import('@/pages/dashboard/infra/WorkOrdersPage').then(m => ({ default: m.WorkOrdersPage })));
const CleaningPage = lazy(() => import('@/pages/dashboard/infra/CleaningPage').then(m => ({ default: m.CleaningPage })));

// New v3.0 Coordination Pages
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
          {/* Overview */}
          <Route index element={<Suspense fallback={<RouteFallback />}><OverviewPage /></Suspense>} />

          {/* Operations */}
          <Route path="gantt" element={<Suspense fallback={<RouteFallback />}><GanttPage /></Suspense>} />
          <Route path="trains" element={<Suspense fallback={<RouteFallback />}><TrainsPage /></Suspense>} />
          <Route path="trains/:trainNo" element={<Suspense fallback={<RouteFallback />}><TrainDetailPage /></Suspense>} />
          <Route path="advisories" element={<Suspense fallback={<RouteFallback />}><AdvisoriesPage /></Suspense>} />
          <Route path="timetable" element={<Suspense fallback={<RouteFallback />}><TimetablePage /></Suspense>} />
          <Route path="blocks" element={<Suspense fallback={<RouteFallback />}><BlockSectionsPage /></Suspense>} />
          <Route path="shunting" element={<Suspense fallback={<RouteFallback />}><ShuntingPage /></Suspense>} />

          {/* Network & Spatial */}
          <Route path="live-map" element={<Suspense fallback={<RouteFallback />}><LiveMapPage /></Suspense>} />
          <Route path="map" element={<Suspense fallback={<RouteFallback />}><LiveMapPage /></Suspense>} />
          <Route path="corridor-gis" element={<Suspense fallback={<RouteFallback />}><CorridorMapPage /></Suspense>} />
          <Route path="yard-map" element={<Suspense fallback={<RouteFallback />}><YardDiagramPage /></Suspense>} />

          {/* Safety */}
          <Route path="safety/tsr" element={<Suspense fallback={<RouteFallback />}><TSRRegistryPage /></Suspense>} />
          <Route path="safety/incidents" element={<Suspense fallback={<RouteFallback />}><IncidentsPage /></Suspense>} />
          <Route path="safety/sop" element={<Suspense fallback={<RouteFallback />}><SOPRunnerPage /></Suspense>} />
          <Route path="safety/lc" element={<Suspense fallback={<RouteFallback />}><LCMonitorPage /></Suspense>} />

          {/* Crew */}
          <Route path="crew" element={<Suspense fallback={<RouteFallback />}><CrewPage /></Suspense>} />

          {/* Infrastructure */}
          <Route path="maintenance" element={<Suspense fallback={<RouteFallback />}><MaintenancePage /></Suspense>} />
          <Route path="assets" element={<Suspense fallback={<RouteFallback />}><AssetsRegistryPage /></Suspense>} />
          <Route path="work-orders" element={<Suspense fallback={<RouteFallback />}><WorkOrdersPage /></Suspense>} />
          <Route path="cleaning" element={<Suspense fallback={<RouteFallback />}><CleaningPage /></Suspense>} />

          {/* Coordination */}
          <Route path="corridor-coordination" element={<Suspense fallback={<RouteFallback />}><CorridorHandoffPage /></Suspense>} />
          <Route path="dfc-coordination" element={<Suspense fallback={<RouteFallback />}><DFCPrecedencePage /></Suspense>} />

          {/* Commercial */}
          <Route path="commercial/delay-certificate" element={<Suspense fallback={<RouteFallback />}><DelayCertificatePage /></Suspense>} />
          <Route path="commercial/announcements" element={<Suspense fallback={<RouteFallback />}><AnnouncementsPage /></Suspense>} />
          <Route path="commercial/stalls" element={<Suspense fallback={<RouteFallback />}><StallsLostFoundPage /></Suspense>} />

          {/* Governance & Governance Admin */}
          <Route path="handover" element={<Suspense fallback={<RouteFallback />}><ShiftHandoverPage /></Suspense>} />
          <Route path="audit" element={<Suspense fallback={<RouteFallback />}><AuditPage /></Suspense>} />
          <Route path="model" element={<Suspense fallback={<RouteFallback />}><ModelPage /></Suspense>} />
          <Route path="admin/users" element={<Suspense fallback={<RouteFallback />}><AdminUsersPage /></Suspense>} />
          <Route path="admin/backups" element={<Suspense fallback={<RouteFallback />}><BackupsIntegrityPage /></Suspense>} />
        </Route>

        {/* 404 Catch-All */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>

      {/* Global Cookieless Consent Banner */}
      <CookieBanner />
    </>
  );
}
