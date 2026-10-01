import axios from 'axios'

// During `vite dev` the /api prefix is proxied to the backend (see vite.config.js).
// In production builds the base URL can be overridden with VITE_API_URL.
const baseURL = import.meta.env.VITE_API_URL || ''

const api = axios.create({ baseURL, timeout: 15000 })

// Attach the JWT access token to every request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-refresh once on a 401, otherwise log the user out.
let isRefreshing = false

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url.includes('/auth/')
    ) {
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken && !isRefreshing) {
        originalRequest._retry = true
        isRefreshing = true
        try {
          const { data } = await axios.post(
            `${baseURL}/api/auth/refresh`,
            { refresh_token: refreshToken },
            { baseURL }
          )
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`
          return api(originalRequest)
        } catch (refreshError) {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.dispatchEvent(new Event('auth:logout'))
          return Promise.reject(refreshError)
        } finally {
          isRefreshing = false
        }
      }
    }
    return Promise.reject(error)
  }
)

// --------------------------------------------------------------------------- //
export const authApi = {
  login: (email, password) =>
    api.post('/api/auth/token', new URLSearchParams({ username: email, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  me: () => api.get('/api/auth/me'),
}

export const resourceApi = {
  list: (params) => api.get('/api/resources/', { params }),
  create: (payload) => api.post('/api/resources/', payload),
}

export const bookingApi = {
  create: (payload) => api.post('/api/bookings/', payload),
  mine: (params) => api.get('/api/bookings/my-reservations', { params }),
  cancel: (id) => api.patch(`/api/bookings/${id}/cancel`),
}

export const auditApi = {
  record: (payload) => api.post('/api/security/audit-log', payload),
  query: (params) => api.get('/api/security/audit-log', { params }),
}

export default api
