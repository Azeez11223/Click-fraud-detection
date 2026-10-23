import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/AppShell'
import { RouteErrorBoundary } from '@/components/RouteErrorBoundary'
import { ProtectedRoute } from '@/auth/ProtectedRoute'
import NotFoundPage from '@/pages/NotFoundPage'

const LoginPage = lazy(() => import('@/pages/LoginPage'))
const SignupPage = lazy(() => import('@/pages/SignupPage'))
const DashboardPage = lazy(() => import('@/features/dashboard/DashboardPage'))
const CampaignsPage = lazy(() => import('@/features/campaigns/CampaignsPage'))
const CampaignDetailPage = lazy(() => import('@/features/campaigns/CampaignDetailPage'))
const SectionPage = lazy(() => import('@/pages/SectionPage'))
const IpManagerPage = lazy(() => import('@/features/ip-manager/IpManagerPage'))
const PredictPage = lazy(() => import('@/features/predict/PredictPage'))
const HistoryPage = lazy(() => import('@/features/history/HistoryPage'))
const AnalyticsPage = lazy(() => import('@/features/analytics/AnalyticsPage'))
const RealtimePage = lazy(() => import('@/features/integrations/RealtimePage'))
const IntegrationsPage = lazy(() => import('@/features/integrations/IntegrationsPage'))

function LoadingPage() {
  return <div className="grid min-h-[50vh] place-items-center text-sm text-muted">Loading page…</div>
}

export default function App() {
  return <RouteErrorBoundary><Suspense fallback={<LoadingPage />}><Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/signup" element={<SignupPage />} />
    <Route element={<ProtectedRoute />}>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/campaigns" element={<CampaignsPage />} />
        <Route path="/campaigns/:campaignId" element={<CampaignDetailPage />} />
        <Route path="/campaigns/:campaignId/live" element={<RealtimePage />} />
        <Route path="/campaigns/:campaignId/integrations" element={<IntegrationsPage />} />
        <Route path="/ip-manager" element={<IpManagerPage />} />
        <Route path="/predict" element={<PredictPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/about" element={<SectionPage />} />
      </Route>
    </Route>
    <Route path="*" element={<NotFoundPage />} />
  </Routes></Suspense></RouteErrorBoundary>
}
