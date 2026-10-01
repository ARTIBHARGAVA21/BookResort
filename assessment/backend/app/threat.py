"""Automated threat detection for incoming request payloads.

The analyzer inspects request bodies, query strings and headers for common
attack signatures (SQL injection, XSS, path traversal, command injection,
SSRF and NoSQL injection) and assigns a threat level:

  HIGH   -> a signature strongly indicating an active attack
  MEDIUM -> suspicious patterns worth reviewing
  LOW    -> nothing remarkable
"""
import re
from typing import Any

# High-confidence attack signatures ------------------------------------------- #
HIGH_SIGNATURES: list[tuple[str, str]] = [
    (r"(?i)(?:'|\")\s*(?:or|and)\s+(?:'1'|1)\s*=\s*(?:'1'|1)", "SQL injection (OR 1=1)"),
    (r"(?i)union\s+(?:all\s+)?select\s+.+\s+from\s+", "SQL injection (UNION SELECT)"),
    (r"(?i);\s*(?:drop|delete|update|insert|truncate)\s+(?:table|database|into)\s+", "SQL injection (stacked DML)"),
    (r"(?i)<\s*script[^>]*>", "XSS (<script>)"),
    (r"(?i)javascript:\s*[a-z]", "XSS (javascript: URI)"),
    (r"(?i)(?:onerror|onload|onmouseover|onclick)\s*=", "XSS (event handler injection)"),
    (r"(?i)\b(?:rm\s+-rf|cat\s+/etc/passwd|wget\s+http|curl\s+http|nc\s+-e)\b", "Command injection"),
    (r"(?i)(?:\$\(|\|\||&&|;)\s*(?:bash|sh|cmd|powershell|whoami|id)\b", "Command injection (shell metacharacters)"),
    (r"(?i)/\.\./\.\.(?:/|\\)", "Path traversal"),
    (r"(?i)(?:%2e%2e|..\%2f|%252e%252e)", "Encoded path traversal"),
    (r"(?i)\b(?:exec|eval|system|popen)\s*\(", "Remote code execution pattern"),
    (r"(?i)\{\s*\$?(?:ne|gt|gte|lt|lte|where|regex)\s*:", "NoSQL injection operator"),
    (r"(?i)file://|data:text/html|expect://|php://", "SSRF / dangerous URI scheme"),
]

# Suspicious but lower confidence ---------------------------------------------- #
MEDIUM_SIGNATURES: list[tuple[str, str]] = [
    (r"(?i)(?:'|\")\s*(?:--|#|/\*)", "SQL comment marker"),
    (r"(?i)\b(?:select|insert|update|delete|drop|alter)\b\s+.+\b(?:from|into|table|where)\b", "SQL keyword sequence"),
    (r"(?i)<\s*(?:img|iframe|svg|body|object|embed)[^>]+onerror", "Potential XSS vector"),
    (r"(?i)<\s*(?:img|iframe|svg|object|embed)\s+src\s*=", "Embedded remote resource"),
    (r"(?i)\b(?:document\.cookie|window\.location|localStorage)\b", "DOM access in payload"),
    (r"(?i)(?:127\.0\.0\.1|localhost|169\.254\.169\.254|0\.0\.0\.0)", "Internal host reference (SSRF risk)"),
    (r"(?i)\\x[0-9a-f]{2}\\x[0-9a-f]{2}", "Hex-encoded payload"),
    (r"(?i)(?:admin|root|sa)\s*[:=]\s*(?:password|passwd|12345|admin)", "Credential stuffing pattern"),
    (r"(?i)(?:{{|\{%).*?(?:}}|%\})", "Server-side template injection marker"),
]

_SENSITIVE_FIELDS = ("password", "token", "secret", "authorization")


def _flatten(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    """Flatten nested dicts/lists into (field, string) pairs for scanning."""
    pairs: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for k, v in value.items():
            pairs.extend(_flatten(v, str(k)))
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            pairs.extend(_flatten(v, f"{prefix}[{i}]"))
    elif value is not None:
        pairs.append((prefix, str(value)))
    return pairs


def analyze_payload(payload: Any) -> tuple[str, list[str]]:
    """Inspect a decoded payload and return (threat_level, reasons)."""
    pairs = _flatten(payload)
    if not pairs:
        return "LOW", []

    # Never raise alerts on cleartext credential fields themselves.
    scan = [(f, v) for f, v in pairs if f.lower() not in _SENSITIVE_FIELDS]

    reasons: list[str] = []
    for field, value in scan:
        if len(value) > 4096:
            reasons.append(f"{field or 'payload'}: oversized input")
            continue
        for pattern, label in HIGH_SIGNATURES:
            if re.search(pattern, value):
                reasons.append(f"{field or 'payload'}: {label}")
        for pattern, label in MEDIUM_SIGNATURES:
            if re.search(pattern, value):
                reasons.append(f"{field or 'payload'}: {label}")

    # Deduplicate while preserving order.
    seen, ordered = set(), []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            ordered.append(r)

    if any(": SQL injection" in r or "command" in r.lower() for r in ordered):
        return "HIGH", ordered
    if ordered:
        return "MEDIUM", ordered
    return "LOW", []
