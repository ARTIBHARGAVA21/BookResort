import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'
import Layout from './components/Layout.jsx'
import Login from './components/Login.jsx'
import Dashboard from './components/Dashboard.jsx'
import AuditLogs from './components/AuditLogs.jsx'

function ProtectedRoute({ children, requireAdmin = false }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="loading">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  if (requireAdmin && user.role !== 'ADMIN') return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route
          path="/audit-logs"
          element={
            <ProtectedRoute requireAdmin>
              <AuditLogs />
            </ProtectedRoute>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
