from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import AuditLog, ThreatLevelEnum, User
from app.schemas import AuditLogCreate, AuditLogOut, AuditLogQuery
from app.threat import analyze_payload

router = APIRouter(prefix=f"{settings.API_PREFIX}/security", tags=["security"])


@router.post(
    "/audit-log",
    response_model=AuditLogOut,
    status_code=201,
    summary="Record a security event",
)
def record_audit_event(
    body: AuditLogCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Persist an explicit security event from an authenticated client.

    The submitted payload is re-analysed server-side; the recorded threat level
    is the higher of the declared level and the assessed level, so a benign
    label cannot mask a suspicious payload.
    """
    assessed_level, assessed_reasons = analyze_payload(body.model_dump())
    final_level = max(
        (body.threat_level, assessed_level),
        key=lambda level: {"LOW": 0, "MEDIUM": 1, "HIGH": 2}[level],
    )
    details = body.details
    if assessed_reasons:
        extra = "; ".join(assessed_reasons)
        details = f"{details} | {extra}" if details else extra

    entry = AuditLog(
        user_id=current_user.id,
        endpoint=body.endpoint,
        method=body.method.upper(),
        ip_address=body.ip_address or request.client.host if request.client else None,
        threat_level=ThreatLevelEnum(final_level),
        event=body.event,
        details=details,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _to_out(entry, db, current_user)


@router.get(
    "/audit-log",
    response_model=list[AuditLogOut],
    summary="Query security audit trails (ADMIN only)",
    dependencies=[Depends(require_admin)],
)
def query_audit_logs(
    threat_level: str | None = Query(None, pattern="^(LOW|MEDIUM|HIGH)$"),
    endpoint: str | None = Query(None),
    user_id: int | None = Query(None),
    event: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Search the audit trail by threat level, endpoint, user or event type."""
    query = db.query(AuditLog)

    if threat_level:
        query = query.filter(AuditLog.threat_level == ThreatLevelEnum(threat_level))
    if endpoint:
        query = query.filter(AuditLog.endpoint.ilike(f"%{endpoint}%"))
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if event:
        query = query.filter(AuditLog.event.ilike(f"%{event}%"))

    entries = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    return [_to_out(e, db) for e in entries]


def _to_out(entry: AuditLog, db: Session, user: User | None = None) -> AuditLogOut:
    out = AuditLogOut.model_validate(entry)
    if not user and entry.user_id:
        user = db.query(User).filter(User.id == entry.user_id).first()
    out.user_email = user.email if user else None
    return out
