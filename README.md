# Bharat Resort Booking Platform

A secured multi-tenant resource booking platform with automated security audit pipeline for thebharatresort.com.

## Project Structure

```
assessment/
├── backend/          # FastAPI backend
├── frontend/         # React + Vite frontend
├── .gitignore
└── Technical Interview Assignment - Arti Bhargava.pdf
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- Git

## Getting Started

### Backend (FastAPI)

```bash
cd assessment/backend
python -m venv venv
source venv/Scripts/activate  # Windows
# or: source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`
Health check: `http://localhost:8000/health`

### Frontend (React + Vite)

```bash
cd assessment/frontend
npm install
npm run dev
```

App will be available at `http://localhost:5173`

The frontend proxies API calls to the backend at `http://localhost:8000`.

## Configuration

- **Database**: SQLite by default (file: `backend/app.db`)
- **Database URL**: Set `DATABASE_URL` env var for PostgreSQL/MySQL
- **CORS**: Modify `CORS_ORIGINS` env var or in `config.py`
- **JWT**: Set `JWT_SECRET` env var for production

## API Endpoints

### Auth
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login

### Resources
- `GET /api/resources` - List resources
- `POST /api/resources` - Create resource (admin)

### Bookings
- `GET /api/bookings` - List bookings
- `POST /api/bookings` - Create booking

### Audit
- `GET /api/audit/logs` - Get audit logs
- Various security endpoints

## Development

- Backend uses FastAPI with SQLAlchemy, Pydantic
- Frontend uses React with React Router and Axios
- API proxy configured in `frontend/vite.config.js`
- Audit middleware logs all state-changing requests with threat assessment