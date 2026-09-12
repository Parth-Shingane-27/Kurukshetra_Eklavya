"""Context-Aware Form Assistance — session handshake + explain-text (browser extension /
mobile toggle backend)."""

from app.core.config import get_settings

ADMIN_HEADERS = {"X-Admin-Token": get_settings().admin_credential}

VERIFIED_SCHEME = {
    "name": "Assist Test Verified Scheme",
    "category": "Test",
    "benefit_type": "cash_transfer",
    "benefit_value_estimate": 5000,
    "rules": [],
    "document_requirements": [],
    "links": {
        "application_url": "https://example-gov-portal.test/apply",
        "application_link_status": "verified",
    },
}

NOT_AVAILABLE_SCHEME = {
    "name": "Assist Test Offline Scheme",
    "category": "Test",
    "benefit_type": "cash_transfer",
    "benefit_value_estimate": 5000,
    "rules": [],
    "document_requirements": [],
    "links": {"application_link_status": "not_available"},
}


async def _create_scheme(client, scheme):
    res = await client.post("/api/schemes", json=scheme, headers=ADMIN_HEADERS)
    assert res.status_code == 201
    return res.json()["id"]


async def test_create_session_for_scheme_with_no_online_application_is_rejected(client):
    scheme_id = await _create_scheme(client, NOT_AVAILABLE_SCHEME)
    res = await client.post("/api/assistance/session", json={"scheme_id": scheme_id})
    assert res.status_code == 422


async def test_create_session_for_unknown_scheme_404s(client):
    res = await client.post("/api/assistance/session", json={"scheme_id": "64b7f0000000000000000000"})
    assert res.status_code == 404


async def test_full_session_handshake_and_explain_text(client):
    scheme_id = await _create_scheme(client, VERIFIED_SCHEME)

    session_res = await client.post("/api/assistance/session", json={"scheme_id": scheme_id})
    assert session_res.status_code == 200
    body = session_res.json()
    assert body["application_url"] == "https://example-gov-portal.test/apply"
    session_id = body["session_id"]

    # Wrong origin is rejected.
    wrong_origin = await client.post(
        "/api/assistance/validate-session",
        json={"session_id": session_id, "origin": "https://not-the-real-portal.test"},
    )
    assert wrong_origin.status_code == 200
    assert wrong_origin.json()["valid"] is False

    # Correct origin (matching the scheme's application_url's own origin) succeeds.
    validate_res = await client.post(
        "/api/assistance/validate-session",
        json={"session_id": session_id, "origin": "https://example-gov-portal.test"},
    )
    assert validate_res.status_code == 200
    validated = validate_res.json()
    assert validated["valid"] is True
    assert validated["scheme_id"] == scheme_id
    token = validated["assistance_token"]
    assert token

    explain_res = await client.post(
        "/api/assistance/explain-text",
        json={"field_label": "Annual family income", "explanation_mode": "text"},
        headers={"Authorization": f"Bearer {token}", "X-Assistance-Origin": "https://example-gov-portal.test"},
    )
    assert explain_res.status_code == 200
    explanation = explain_res.json()
    assert explanation["question_meaning"]
    # BR-020: the eligibility caution is always present, never left to model discretion.
    assert "eligibility" in (explanation["important_caution"] or "").lower()


async def test_explain_text_rejects_wrong_origin(client):
    scheme_id = await _create_scheme(client, VERIFIED_SCHEME)
    session_id = (await client.post("/api/assistance/session", json={"scheme_id": scheme_id})).json()["session_id"]
    token = (
        await client.post(
            "/api/assistance/validate-session",
            json={"session_id": session_id, "origin": "https://example-gov-portal.test"},
        )
    ).json()["assistance_token"]

    res = await client.post(
        "/api/assistance/explain-text",
        json={"field_label": "Annual family income"},
        headers={"Authorization": f"Bearer {token}", "X-Assistance-Origin": "https://a-different-site.test"},
    )
    assert res.status_code == 403


async def test_explain_text_rejects_missing_token(client):
    res = await client.post(
        "/api/assistance/explain-text",
        json={"field_label": "Annual family income"},
        headers={"X-Assistance-Origin": "https://example-gov-portal.test"},
    )
    assert res.status_code == 401


async def test_login_token_cannot_be_used_as_an_assistance_token(client):
    """A different `typ` claim means the two token kinds are never interchangeable."""
    await client.post(
        "/api/auth/register", json={"email": "assist_cross@example.com", "password": "s3cret-pass", "role": "citizen"}
    )
    login_res = await client.post(
        "/api/auth/login", json={"email": "assist_cross@example.com", "password": "s3cret-pass"}
    )
    login_token = login_res.json()["access_token"]

    res = await client.post(
        "/api/assistance/explain-text",
        json={"field_label": "Annual family income"},
        headers={"Authorization": f"Bearer {login_token}", "X-Assistance-Origin": "https://example-gov-portal.test"},
    )
    assert res.status_code == 401


async def _get_assistance_token(client, scheme_id):
    session_id = (await client.post("/api/assistance/session", json={"scheme_id": scheme_id})).json()["session_id"]
    validated = await client.post(
        "/api/assistance/validate-session",
        json={"session_id": session_id, "origin": "https://example-gov-portal.test"},
    )
    return validated.json()["assistance_token"]


async def test_explain_screenshot_with_no_gemini_key_returns_honest_clarification(client):
    """No GEMINI_API_KEY is configured in the test environment — transcription can't happen,
    so this must degrade to an honest "couldn't read it" response, never a fabricated
    explanation of an image the backend never actually looked at."""
    scheme_id = await _create_scheme(client, VERIFIED_SCHEME)
    token = await _get_assistance_token(client, scheme_id)

    tiny_png_base64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    res = await client.post(
        "/api/assistance/explain-screenshot",
        json={"screenshot_base64": tiny_png_base64, "mime_type": "image/png"},
        headers={"Authorization": f"Bearer {token}", "X-Assistance-Origin": "https://example-gov-portal.test"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["needs_clarification"] is True
    assert body["confidence"] == 0.0


async def test_explain_screenshot_rejects_oversized_image(client):
    scheme_id = await _create_scheme(client, VERIFIED_SCHEME)
    token = await _get_assistance_token(client, scheme_id)

    settings = get_settings()
    # Comfortably over the configured limit once base64-decoded.
    oversized_raw = b"0" * (settings.assistance_screenshot_max_bytes + 1000)
    import base64

    oversized_base64 = base64.b64encode(oversized_raw).decode()

    res = await client.post(
        "/api/assistance/explain-screenshot",
        json={"screenshot_base64": oversized_base64, "mime_type": "image/png"},
        headers={"Authorization": f"Bearer {token}", "X-Assistance-Origin": "https://example-gov-portal.test"},
    )
    assert res.status_code == 422


async def test_explain_screenshot_rejects_invalid_base64(client):
    scheme_id = await _create_scheme(client, VERIFIED_SCHEME)
    token = await _get_assistance_token(client, scheme_id)

    res = await client.post(
        "/api/assistance/explain-screenshot",
        json={"screenshot_base64": "not-valid-base64!!!", "mime_type": "image/png"},
        headers={"Authorization": f"Bearer {token}", "X-Assistance-Origin": "https://example-gov-portal.test"},
    )
    assert res.status_code == 422


async def test_explain_screenshot_requires_valid_assistance_session(client):
    res = await client.post(
        "/api/assistance/explain-screenshot",
        json={"screenshot_base64": "aGVsbG8=", "mime_type": "image/png"},
        headers={"X-Assistance-Origin": "https://example-gov-portal.test"},
    )
    assert res.status_code == 401
