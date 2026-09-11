"""FR-016 — Two-step (email+password+OTP) authentication."""

from app.core.config import get_settings

ADMIN_BOOTSTRAP = {"admin_bootstrap_credential": get_settings().admin_credential}


async def _register_and_login(client, email="citizen@example.com", password="s3cret-pass", role="citizen"):
    payload = {"email": email, "password": password, "role": role}
    if role == "admin":
        payload.update(ADMIN_BOOTSTRAP)
    res = await client.post("/api/auth/register", json=payload)
    assert res.status_code == 201, res.text

    login_res = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200, login_res.text
    body = login_res.json()
    assert body["debug_otp"] is not None  # no RESEND_API_KEY configured in tests

    verify_res = await client.post(
        "/api/auth/verify-otp", json={"pending_token": body["pending_token"], "code": body["debug_otp"]}
    )
    assert verify_res.status_code == 200, verify_res.text
    return verify_res.json()


async def test_register_creates_citizen_account(client):
    res = await client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "s3cret-pass", "role": "citizen"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "new@example.com"
    assert body["role"] == "citizen"


async def test_register_duplicate_email_rejected(client):
    payload = {"email": "dupe@example.com", "password": "s3cret-pass", "role": "citizen"}
    await client.post("/api/auth/register", json=payload)
    res = await client.post("/api/auth/register", json=payload)
    assert res.status_code == 409


async def test_register_admin_requires_bootstrap_credential(client):
    res = await client.post(
        "/api/auth/register", json={"email": "admin1@example.com", "password": "s3cret-pass", "role": "admin"}
    )
    assert res.status_code == 403


async def test_register_admin_with_correct_bootstrap_credential(client):
    res = await client.post(
        "/api/auth/register",
        json={
            "email": "admin2@example.com",
            "password": "s3cret-pass",
            "role": "admin",
            **ADMIN_BOOTSTRAP,
        },
    )
    assert res.status_code == 201
    assert res.json()["role"] == "admin"


async def test_login_wrong_password_rejected(client):
    await client.post(
        "/api/auth/register", json={"email": "wrongpw@example.com", "password": "s3cret-pass", "role": "citizen"}
    )
    res = await client.post("/api/auth/login", json={"email": "wrongpw@example.com", "password": "nope"})
    assert res.status_code == 401


async def test_login_unknown_email_rejected(client):
    res = await client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "whatever"})
    assert res.status_code == 401


async def test_full_two_step_login_issues_token_and_me_works(client):
    tokens = await _register_and_login(client, email="fullflow@example.com")
    assert tokens["token_type"] == "bearer"
    assert tokens["user"]["email"] == "fullflow@example.com"

    me_res = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "fullflow@example.com"


async def test_me_without_token_rejected(client):
    res = await client.get("/api/auth/me")
    assert res.status_code == 401


async def test_verify_otp_wrong_code_rejected(client):
    await client.post(
        "/api/auth/register", json={"email": "badotp@example.com", "password": "s3cret-pass", "role": "citizen"}
    )
    login_res = await client.post("/api/auth/login", json={"email": "badotp@example.com", "password": "s3cret-pass"})
    pending_token = login_res.json()["pending_token"]

    res = await client.post("/api/auth/verify-otp", json={"pending_token": pending_token, "code": "000000"})
    assert res.status_code == 401


async def test_verify_otp_lockout_after_max_attempts(client):
    await client.post(
        "/api/auth/register", json={"email": "lockout@example.com", "password": "s3cret-pass", "role": "citizen"}
    )
    login_res = await client.post("/api/auth/login", json={"email": "lockout@example.com", "password": "s3cret-pass"})
    pending_token = login_res.json()["pending_token"]

    for _ in range(get_settings().otp_max_attempts):
        res = await client.post("/api/auth/verify-otp", json={"pending_token": pending_token, "code": "000000"})
        assert res.status_code == 401

    # pending login is now gone even if the *correct* code is supplied afterward
    res = await client.post("/api/auth/verify-otp", json={"pending_token": pending_token, "code": "000000"})
    assert res.status_code == 401


async def test_admin_login_flow_grants_admin_scheme_write_access(client):
    tokens = await _register_and_login(client, email="curator@example.com", role="admin")
    scheme = {
        "name": "Two-Step Test Scheme",
        "category": "Social welfare & Empowerment",
        "benefit_type": "monthly_pension",
        "benefit_value_estimate": 5000,
        "rules": [{"field_name": "marital_status", "operator": "=", "value": "widowed"}],
        "document_requirements": [{"document_type": "Aadhaar Card", "is_mandatory": True}],
    }
    res = await client.post(
        "/api/schemes", json=scheme, headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert res.status_code == 201


async def test_legacy_x_admin_token_still_works_alongside_new_login(client):
    """Backward compatibility: the pre-existing shared-secret header must keep working so the
    prior admin-token test suite (test_admin_schemes.py) is unaffected by this migration."""
    scheme = {
        "name": "Legacy Header Scheme",
        "category": "Social welfare & Empowerment",
        "benefit_type": "monthly_pension",
        "benefit_value_estimate": 1000,
        "rules": [{"field_name": "marital_status", "operator": "=", "value": "widowed"}],
        "document_requirements": [],
    }
    res = await client.post(
        "/api/schemes", json=scheme, headers={"X-Admin-Token": get_settings().admin_credential}
    )
    assert res.status_code == 201


async def test_citizen_created_anonymously_is_still_publicly_readable(client):
    """Backward compatibility: profiles created with no auth (the original flow) remain open,
    exactly matching current behavior for every other existing test in this suite."""
    res = await client.post(
        "/api/citizens",
        json={"name": "Anon Citizen", "date_of_birth": "1990-01-01", "state": "Bihar", "district": "Patna"},
    )
    assert res.status_code == 201
    citizen_id = res.json()["id"]
    assert res.json()["owner_user_id"] is None

    get_res = await client.get(f"/api/citizens/{citizen_id}")
    assert get_res.status_code == 200


async def test_citizen_created_while_logged_in_is_owned_and_protected(client):
    tokens = await _register_and_login(client, email="owner@example.com")
    auth_headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    create_res = await client.post(
        "/api/citizens",
        json={"name": "Owned Citizen", "date_of_birth": "1990-01-01", "state": "Bihar", "district": "Patna"},
        headers=auth_headers,
    )
    assert create_res.status_code == 201
    citizen_id = create_res.json()["id"]
    assert create_res.json()["owner_user_id"] == tokens["user"]["id"]

    # The owner can read their own profile.
    own_get = await client.get(f"/api/citizens/{citizen_id}", headers=auth_headers)
    assert own_get.status_code == 200

    # An unauthenticated request is now denied (unlike the anonymous-profile case above).
    anon_get = await client.get(f"/api/citizens/{citizen_id}")
    assert anon_get.status_code == 403

    # A different logged-in citizen is also denied.
    other_tokens = await _register_and_login(client, email="other@example.com")
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}
    other_get = await client.get(f"/api/citizens/{citizen_id}", headers=other_headers)
    assert other_get.status_code == 403

    # An admin can still read it.
    admin_tokens = await _register_and_login(client, email="admin3@example.com", role="admin")
    admin_headers = {"Authorization": f"Bearer {admin_tokens['access_token']}"}
    admin_get = await client.get(f"/api/citizens/{citizen_id}", headers=admin_headers)
    assert admin_get.status_code == 200
