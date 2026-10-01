import { useState } from 'react'
import { bookingApi } from '../api.js'

function nightsBetween(checkIn, checkOut) {
  const a = new Date(checkIn)
  const b = new Date(checkOut)
  return Math.round((b - a) / 86400000)
}

function fmt(n) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)
}

export default function BookingModal({ resource, defaultCheckIn, defaultCheckOut, onClose, onBooked }) {
  const [checkIn, setCheckIn] = useState(defaultCheckIn)
  const [checkOut, setCheckOut] = useState(defaultCheckOut)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const nights = nightsBetween(checkIn, checkOut)
  const valid = nights > 0
  const total = valid ? nights * Number(resource.daily_rate) : 0

  const handleSubmit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await bookingApi.create({
        resource_id: resource.id,
        check_in: checkIn,
        check_out: checkOut,
      })
      onBooked()
    } catch (err) {
      setError(err.response?.data?.detail || 'Booking failed. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>Book {resource.name}</h3>
          <button className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <label>
              Check-in
              <input type="date" value={checkIn} onChange={(e) => setCheckIn(e.target.value)} required />
            </label>
            <label>
              Check-out
              <input type="date" value={checkOut} onChange={(e) => setCheckOut(e.target.value)} required />
            </label>
          </div>

          <div className="price-summary">
            <div className="price-line">
              <span>Daily rate</span>
              <span>{fmt(resource.daily_rate)}</span>
            </div>
            <div className="price-line">
              <span>Nights</span>
              <span>{valid ? nights : '—'}</span>
            </div>
            <div className="price-line total">
              <span>Total price</span>
              <span>{fmt(total)}</span>
            </div>
          </div>

          {nights <= 0 && (
            <div className="alert alert-error">Check-out must be after check-in.</div>
          )}
          {error && <div className="alert alert-error">{error}</div>}

          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={busy || !valid}>
              {busy ? 'Confirming…' : 'Confirm booking'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
