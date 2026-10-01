import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext.jsx'

const DEMO_ACCOUNTS = [
  { label: 'Admin', email: 'admin@thebharatresort.com', password: 'Admin@12345' },
  { label: 'Staff', email: 'staff@thebharatresort.com', password: 'Staff@12345' },
  { label: 'Customer', email: 'customer@thebharatresort.com', password: 'Guest@12345' },
]

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('admin@thebharatresort.com')
  const [password, setPassword] = useState('Admin@12345')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Check your credentials.')
    } finally {
      setBusy(false)
    }
  }

  const fillDemo = (account) => {
    setEmail(account.email)
    setPassword(account.password)
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="brand center">
          <span className="logo big">🏝️</span>
          <h1>The Bharat Resort</h1>
          <p className="tagline">Secured Booking &amp; Security Operations Console</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>
          {error && <div className="alert alert-error">{error}</div>}
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div className="demo-accounts">
          <p className="hint">Demo accounts (click to fill):</p>
          <div className="demo-buttons">
            {DEMO_ACCOUNTS.map((a) => (
              <button
                key={a.label}
                type="button"
                className="btn btn-outline"
                onClick={() => fillDemo(a)}
              >
                {a.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
