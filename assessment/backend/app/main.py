from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware import AuditMiddleware
from app.routers import audit, auth, bookings, resources
from app.seed import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Secured multi-tenant resource booking platform with automated security "
        "audit pipeline (thebharatresort.com)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Security pipeline: audit + threat tagging on every state-changing request.
app.add_middleware(AuditMiddleware)

# CORS for the React frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Threat-Level"],
)

app.include_router(auth.router)
app.include_router(resources.router)
app.include_router(bookings.router)
app.include_router(audit.router)


@app.get("/health", tags=["health"], summary="Liveness probe")
def health():
    return {"status": "ok", "service": settings.PROJECT_NAME}
