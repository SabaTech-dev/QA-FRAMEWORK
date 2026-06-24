import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useState } from 'react'
import Layout from './components/Layout'
import Dashboard from './pages/DashboardEnhanced'
import TestSuites from './pages/TestSuites'
import TestCases from './pages/TestCases'
import Executions from './pages/Executions'
import Integrations from './pages/Integrations'
import Billing from './pages/Billing'
import SelfHealing from './pages/SelfHealing'
import Settings from './pages/Settings'
import Login from './pages/Login'
import Register from './pages/Register'
import Landing from './pages/Landing'
import ForgotPassword from './pages/ForgotPassword'
import Onboarding from './pages/Onboarding'
import NotFound from './pages/NotFound'
import useAuthStore from './stores/authStore'

function App() {
  const { isAuthenticated, needsOnboarding } = useAuthStore()
  const [sidebarOpen, setSidebarOpen] = useState(true)

  // Redirect authenticated users who need onboarding
  const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
    if (!isAuthenticated) {
      return <Navigate to="/login" replace />
    }
    if (needsOnboarding) {
      return <Navigate to="/onboarding" replace />
    }
    return <>{children}</>
  }

  const OnboardingRoute = () => {
    if (!isAuthenticated) {
      return <Navigate to="/login" replace />
    }
    if (!needsOnboarding) {
      return <Navigate to="/dashboard" replace />
    }
    return <Onboarding />
  }

  return (
    <Router>
      <Routes>
        {/* Public routes - ALWAYS accessible */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />

        {/* Onboarding route - for new users */}
        <Route path="/onboarding" element={<OnboardingRoute />} />

        {/* Protected routes - Require authentication + completed onboarding */}
        <Route path="/dashboard" element={
          <ProtectedRoute>
            <Layout sidebarOpen={sidebarOpen} onSidebarToggle={() => setSidebarOpen(!sidebarOpen)}>
              <Dashboard />
            </Layout>
          </ProtectedRoute>
        } />
        <Route path="/suites" element={
          <ProtectedRoute>
            <Layout sidebarOpen={sidebarOpen} onSidebarToggle={() => setSidebarOpen(!sidebarOpen)}>
              <TestSuites />
            </Layout>
          </ProtectedRoute>
        } />
        <Route path="/suites/:suiteId/cases" element={
          <ProtectedRoute>
            <Layout sidebarOpen={sidebarOpen} onSidebarToggle={() => setSidebarOpen(!sidebarOpen)}>
              <TestCases />
            </Layout>
          </ProtectedRoute>
        } />
        <Route path="/cases" element={
          <ProtectedRoute>
            <Layout sidebarOpen={sidebarOpen} onSidebarToggle={() => setSidebarOpen(!sidebarOpen)}>
              <TestCases />
            </Layout>
          </ProtectedRoute>
        } />
        <Route path="/executions" element={
          <ProtectedRoute>
            <Layout sidebarOpen={sidebarOpen} onSidebarToggle={() => setSidebarOpen(!sidebarOpen)}>
              <Executions />
            </Layout>
          </ProtectedRoute>
        } />
        <Route path="/integrations" element={
          <ProtectedRoute>
            <Layout sidebarOpen={sidebarOpen} onSidebarToggle={() => setSidebarOpen(!sidebarOpen)}>
              <Integrations />
            </Layout>
          </ProtectedRoute>
        } />
        <Route path="/billing" element={
          <ProtectedRoute>
            <Layout sidebarOpen={sidebarOpen} onSidebarToggle={() => setSidebarOpen(!sidebarOpen)}>
              <Billing />
            </Layout>
          </ProtectedRoute>
        } />
        <Route path="/self-healing" element={
          <ProtectedRoute>
            <Layout sidebarOpen={sidebarOpen} onSidebarToggle={() => setSidebarOpen(!sidebarOpen)}>
              <SelfHealing />
            </Layout>
          </ProtectedRoute>
        } />
        <Route path="/settings" element={
          <ProtectedRoute>
            <Layout sidebarOpen={sidebarOpen} onSidebarToggle={() => setSidebarOpen(!sidebarOpen)}>
              <Settings />
            </Layout>
          </ProtectedRoute>
        } />

        {/* Catch-all route - 404 */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  )
}

export default App