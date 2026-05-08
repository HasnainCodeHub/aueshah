"""Integration tests for the production CORS lockdown.

Asserts the FastAPI app rejects unknown browser origins and accepts the
configured allowlist (aueshah.com / www.aueshah.com by default), and that
the Private-Network-Access middleware can't be used to slip past the
lockdown by reflecting any caller's origin.
"""
from __future__ import annotations

from app.config.settings import settings


def test_allowed_origin_gets_cors_header_back(client):
    """A browser preflight from https://aueshah.com must succeed."""
    r = client.options(
        "/chat",
        headers={
            "Origin": "https://aueshah.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code == 200, f"preflight rejected for allowed origin (got {r.status_code})"
    assert r.headers.get("access-control-allow-origin") == "https://aueshah.com"


def test_www_subdomain_also_allowed(client):
    """www.aueshah.com is in the default allowlist."""
    r = client.options(
        "/chat",
        headers={
            "Origin": "https://www.aueshah.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "https://www.aueshah.com"


def test_disallowed_origin_does_not_get_cors_header(client):
    """A preflight from a rogue origin must NOT receive an allow-origin header.

    The browser is what enforces CORS — but it relies on the SERVER not
    reflecting an unknown origin. Without the header, the browser blocks the
    real request, which is the lockdown working.
    """
    r = client.options(
        "/chat",
        headers={
            "Origin": "https://evil-attacker.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    # Starlette's CORSMiddleware returns 400 for disallowed-origin preflights
    # in some versions, 200 with no allow-origin in others. Both are correct
    # lockdown behavior — what matters is the absence of the allow-origin
    # header for the rogue origin.
    assert r.headers.get("access-control-allow-origin") != "https://evil-attacker.example"


def test_actual_request_from_disallowed_origin_strips_cors_header(client):
    """A real (non-preflight) request from an unknown origin should not
    receive a permissive Access-Control-Allow-Origin echoing the attacker."""
    r = client.get(
        "/health",
        headers={"Origin": "https://evil-attacker.example"},
    )
    # /health itself works — CORS doesn't block server-side. But the response
    # must not advertise the rogue origin as allowed.
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") != "https://evil-attacker.example"


def test_pna_preflight_rejects_unknown_origin(client):
    """The Private-Network-Access middleware was the bypass risk: it used to
    echo back ANY origin. After lockdown, an unknown origin's PNA preflight
    must NOT receive Access-Control-Allow-Origin echoing it."""
    r = client.options(
        "/chat",
        headers={
            "Origin": "https://evil-attacker.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Private-Network": "true",
        },
    )
    # PNA path now returns 403 for unknown origins.
    assert r.status_code == 403
    assert r.headers.get("access-control-allow-origin") != "https://evil-attacker.example"


def test_pna_preflight_accepts_allowed_origin(client):
    """Allowed origins must still receive PNA permission so localhost dev works
    when configured."""
    r = client.options(
        "/chat",
        headers={
            "Origin": "https://aueshah.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Private-Network": "true",
        },
    )
    assert r.status_code == 204
    assert r.headers.get("access-control-allow-origin") == "https://aueshah.com"
    assert r.headers.get("access-control-allow-private-network") == "true"


def test_settings_cors_origins_parses_default():
    """Sanity: the default allowlist contains the two production origins."""
    origins = settings.cors_origins
    assert "https://aueshah.com" in origins
    assert "https://www.aueshah.com" in origins


def test_settings_cors_origins_handles_extra_whitespace_and_blanks():
    """Comma-list parser must tolerate trailing blanks like
    'https://a.com,,https://b.com,' without crashing."""
    from app.config.settings import Settings

    s = Settings(cors_allowed_origins="https://a.com, , https://b.com,")
    assert s.cors_origins == ["https://a.com", "https://b.com"]
