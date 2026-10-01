import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext.jsx'

export default function Layout() {
  const { user, logout, isAdmin } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="layout">
      <header className="topbar">
        <div className="brand">
          <span className="logo">🏝️</span>
          <div>
            <h1>The Bharat Resort</h1>
            <span className="tagline">Booking &amp; Security Operations</span>
          </div>
        </div>
        <nav className="nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : '')}>
            Bookings
          </NavLink>
          {isAdmin && (
            <NavLink
              to="/audit-logs"
              className={({ isActive }) => (isActive ? 'active' : '')}
            >
              Security Audit
            </NavLink>
          )}
        </nav>
        <div className="user-chip">
          <div className="user-meta">
            <strong>{user?.full_name}</strong>
            <span className="role-badge">{user?.role}</span>
          </div>
          <button className="btn btn-ghost" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
      <footer className="footer">
        <span>Secured Multi-Tenant Resource Booking Platform</span>
        <span>Automated Security Audit Pipeline</span>
      </footer>
    </div>
  )
}
