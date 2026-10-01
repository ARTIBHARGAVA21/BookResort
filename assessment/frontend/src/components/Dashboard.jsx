import { useEffect, useState, useCallback } from 'react'
import { resourceApi, bookingApi } from '../api.js'
import { useAuth } from '../AuthContext.jsx'
import BookingModal from './BookingModal.jsx'

const CATEGORIES = ['ROOM', 'SUITE', 'HALL']

function todayPlus(days) {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

export default function Dashboard() {
  const { user, isStaff } = useAuth()
  const [resources, setResources] = useState([])
  const [reservations, setReservations] = useState([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState(null)

  // Filters
  const [category, setCategory] = useState('')
  const [checkIn, setCheckIn] = useState(todayPlus(1))
  const [checkOut, setCheckOut] = useState(todayPlus(3))

  const [bookingTarget, setBookingTarget] = useState(null)

  const loadResources = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (category) params.category = category
      if (checkIn && checkOut) {
        params.check_in = checkIn
        params.check_out = checkOut
      }
      const { data } = await resourceApi.list(params)
      setResources(data)
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to load resources' })
    } finally {
      setLoading(false)
    }
  }, [category, checkIn, checkOut])

  const loadReservations = useCallback(async () => {
    try {
      const { data } = await bookingApi.mine()
      setReservations(data)
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to load reservations' })
    }
  }, [])

  useEffect(() => {
    loadResources()
  }, [loadResources])

  useEffect(() => {
    loadReservations()
  }, [loadReservations])

  const resetFilters = () => {
    setCategory('')
    setCheckIn(todayPlus(1))
    setCheckOut(todayPlus(3))
  }

  const handleBooked = () => {
    setBookingTarget(null)
    loadResources()
    loadReservations()
    setMessage({ type: 'success', text: 'Booking confirmed. See it under My Reservations.' })
  }

  const handleCancel = async (id) => {
    if (!window.confirm('Cancel this reservation?')) return
    try {
      await bookingApi.cancel(id)
      loadReservations()
      loadResources()
      setMessage({ type: 'success', text: 'Reservation cancelled.' })
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Cancel failed' })
    }
  }

  const fmt = (n) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)

  return (
    <div className="dashboard">
      {message && (
        <div className={`alert alert-${message.type}`}>
          {message.text}
          <button className="alert-close" onClick={() => setMessage(null)} aria-label="Dismiss">
            ×
          </button>
        </div>
      )}

      <section className="panel">
        <div className="panel-head">
          <h2>Available Resources</h2>
          <span className="muted">{resources.length} shown</span>
        </div>

        <div className="filters">
          <label>
            Category
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">All categories</option>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <label>
            Check-in
            <input type="date" value={checkIn} onChange={(e) => setCheckIn(e.target.value)} />
          </label>
          <label>
            Check-out
            <input type="date" value={checkOut} onChange={(e) => setCheckOut(e.target.value)} />
          </label>
          <button className="btn btn-ghost" onClick={resetFilters}>
            Reset
          </button>
        </div>

        {loading ? (
          <div className="loading">Loading resources…</div>
        ) : resources.length === 0 ? (
          <div className="empty">
            <h3>No resources available</h3>
            <p className="muted">Try a different date range or category.</p>
          </div>
        ) : (
          <div className="resource-grid">
            {resources.map((r) => (
              <article key={r.id} className="resource-card">
                <div className="resource-icon">{r.category === 'ROOM' ? '🛏️' : r.category === 'SUITE' ? '🛌' : '🏛️'}</div>
                <h3>{r.name}</h3>
                <div className="resource-meta">
                  <span className="chip">{r.category}</span>
                  <span className="rate">{fmt(r.daily_rate)} <small>/ night</small></span>
                </div>
                <button className="btn btn-primary" onClick={() => setBookingTarget(r)}>
                  Book now
                </button>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>My Reservations</h2>
          <span className="muted">Welcome back, {user?.full_name?.split(' ')[0]}</span>
        </div>

        {reservations.length === 0 ? (
          <div className="empty">
            <p className="muted">You have no reservations yet.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Resource</th>
                  <th>Check-in</th>
                  <th>Check-out</th>
                  <th>Nights</th>
                  <th>Total</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {reservations.map((b) => {
                  const nights = Math.round(
                    (new Date(b.check_out) - new Date(b.check_in)) / 86400000
                  )
                  return (
                    <tr key={b.id}>
                      <td>{b.resource_name || `Resource #${b.resource_id}`}</td>
                      <td>{b.check_in}</td>
                      <td>{b.check_out}</td>
                      <td>{nights}</td>
                      <td>{fmt(b.total_price)}</td>
                      <td>
                        <span className={`status status-${b.status.toLowerCase()}`}>{b.status}</span>
                      </td>
                      <td>
                        {b.status === 'CONFIRMED' && (
                          <button
                            className="btn btn-danger btn-sm"
                            onClick={() => handleCancel(b.id)}
                          >
                            Cancel
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {bookingTarget && (
        <BookingModal
          resource={bookingTarget}
          defaultCheckIn={checkIn}
          defaultCheckOut={checkOut}
          onClose={() => setBookingTarget(null)}
          onBooked={handleBooked}
        />
      )}
    </div>
  )
}
