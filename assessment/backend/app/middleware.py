import json
import logging
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.database import SessionLocal
from app.models import AuditLog, ThreatLevelEnum
from app.threat import analyze_payload

logger = logging.getLogger("audit")

WRITE_METHODS = {"POST", "PUT", "PATCH"}


def _client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else None


class AuditMiddleware(BaseHTTPMiddleware):
    """Automated threat logging.

    Intercepts every state-changing request, decodes and inspects its payload
    for attack signatures, and writes an audit trail entry tagged with the
    resulting threat level. Read-only requests are only logged when the query
    string itself is flagged as suspicious.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        method = request.method.upper()
        path = request.url.path
        threat_level = "LOW"
        reasons: list[str] = []
        payload_sample: Optional[str] = None
        log_this = method in WRITE_METHODS

        if method in WRITE_METHODS:
            raw_body = await request.body()

            # Re-buffer the body so downstream handlers still receive it.
            body_bytes = raw_body

            async def receive() -> dict:
                return {"type": "http.request", "body": body_bytes, "more_body": False}

            request = Request(request.scope, receive)

            if raw_body:
                try:
                    parsed = json.loads(raw_body.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    parsed = raw_body.decode("utf-8", errors="replace")[:512]
                threat_level, reasons = analyze_payload(parsed)
                payload_sample = str(parsed)[:500]
        else:
            query = dict(request.query_params)
            if query:
                threat_level, reasons = analyze_payload(query)
                if threat_level != "LOW":
                    log_this = True

        request.state.threat_level = threat_level
        request.state.threat_reasons = reasons

        response: Response = await call_next(request)

        # Tag the response so clients/sec tooling can see the assessment.
        response.headers["X-Threat-Level"] = threat_level

        if log_this:
            self._record(
                endpoint=path,
                method=method,
                ip=_client_ip(request),
                threat_level=threat_level,
                reasons=reasons,
                payload_sample=payload_sample,
            )

        return response

    @staticmethod
    def _record(
        endpoint: str,
        method: str,
        ip: Optional[str],
        threat_level: str,
        reasons: list[str],
        payload_sample: Optional[str],
    ) -> None:
        details = "; ".join(reasons) if reasons else None
        if payload_sample and details:
            details = f"{details} | payload={payload_sample}"
        elif payload_sample:
            details = f"payload={payload_sample}"

        db = SessionLocal()
        try:
            db.add(
                AuditLog(
                    endpoint=endpoint,
                    method=method,
                    ip_address=ip,
                    threat_level=ThreatLevelEnum(threat_level),
                    event="REQUEST" if threat_level == "LOW" else "FLAGGED_REQUEST",
                    details=details,
                )
            )
            db.commit()
        except Exception as exc:  # never break a request over audit logging
            db.rollback()
            logger.error("Failed to write audit log: %s", exc)
        finally:
            db.close()
