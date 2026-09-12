"""Citizen document uploads — plain document management, deliberately not verification
(no parsing/authenticity claims; see app/models/document_upload.py)."""

import base64

from app.core.config import get_settings

ADMIN_BOOTSTRAP = {"admin_bootstrap_credential": get_settings().admin_credential}
SAMPLE_BYTES = b"%PDF-1.4 fake content for a test upload, not a real PDF"
SAMPLE_B64 = base64.b64encode(SAMPLE_BYTES).decode("ascii")


async def _login(client, email, role="citizen"):
    payload = {"email": email, "password": "s3cret-pass", "role": role}
    if role == "admin":
        payload.update(ADMIN_BOOTSTRAP)
    await client.post("/api/auth/register", json=payload)
    login_res = await client.post("/api/auth/login", json={"email": email, "password": "s3cret-pass"})
    return login_res.json()


async def _make_citizen(client, headers=None):
    res = await client.post(
        "/api/citizens",
        json={
            "name": "Doc Upload Test",
            "date_of_birth": "1990-01-01",
            "state": "Bihar",
            "district": "Patna",
        },
        headers=headers or {},
    )
    return res.json()["id"]


async def test_upload_list_and_download_document(client):
    citizen_id = await _make_citizen(client)

    upload_res = await client.post(
        f"/api/citizens/{citizen_id}/document-uploads",
        json={"document_type": "Aadhaar Card", "filename": "aadhaar.pdf", "content_type": "application/pdf", "file_base64": SAMPLE_B64},
    )
    assert upload_res.status_code == 201
    upload = upload_res.json()
    assert upload["document_type"] == "Aadhaar Card"
    assert upload["size_bytes"] == len(SAMPLE_BYTES)
    assert "file_base64" not in upload

    list_res = await client.get(f"/api/citizens/{citizen_id}/document-uploads")
    assert list_res.status_code == 200
    listed = list_res.json()
    assert len(listed) == 1
    assert listed[0]["id"] == upload["id"]

    content_res = await client.get(f"/api/citizens/{citizen_id}/document-uploads/{upload['id']}/content")
    assert content_res.status_code == 200
    content = content_res.json()
    assert base64.b64decode(content["file_base64"]) == SAMPLE_BYTES
    assert content["filename"] == "aadhaar.pdf"


async def test_upload_auto_marks_document_held_on_profile(client):
    citizen_id = await _make_citizen(client)

    await client.post(
        f"/api/citizens/{citizen_id}/document-uploads",
        json={"document_type": "Income Certificate", "filename": "income.pdf", "content_type": "application/pdf", "file_base64": SAMPLE_B64},
    )

    citizen_res = await client.get(f"/api/citizens/{citizen_id}")
    documents = citizen_res.json()["documents"]
    assert any(d["document_type"] == "Income Certificate" and d["held"] is True for d in documents)


async def test_upload_rejects_oversized_file(client, monkeypatch):
    citizen_id = await _make_citizen(client)
    from app.core.config import get_settings as real_get_settings

    class _TinyLimitSettings:
        def __getattr__(self, name):
            return getattr(real_get_settings(), name)

        @property
        def document_upload_max_bytes(self):
            return 10

    import app.models.document_upload as document_upload_module

    monkeypatch.setattr(document_upload_module, "get_settings", lambda: _TinyLimitSettings())

    res = await client.post(
        f"/api/citizens/{citizen_id}/document-uploads",
        json={"document_type": "Aadhaar Card", "filename": "big.pdf", "content_type": "application/pdf", "file_base64": SAMPLE_B64},
    )
    assert res.status_code == 422


async def test_upload_rejects_invalid_base64(client):
    citizen_id = await _make_citizen(client)
    res = await client.post(
        f"/api/citizens/{citizen_id}/document-uploads",
        json={"document_type": "Aadhaar Card", "filename": "x.pdf", "content_type": "application/pdf", "file_base64": "not-valid-base64!!"},
    )
    assert res.status_code == 422


async def test_delete_document(client):
    citizen_id = await _make_citizen(client)
    upload_res = await client.post(
        f"/api/citizens/{citizen_id}/document-uploads",
        json={"document_type": "Aadhaar Card", "filename": "aadhaar.pdf", "content_type": "application/pdf", "file_base64": SAMPLE_B64},
    )
    upload_id = upload_res.json()["id"]

    del_res = await client.delete(f"/api/citizens/{citizen_id}/document-uploads/{upload_id}")
    assert del_res.status_code == 204

    list_res = await client.get(f"/api/citizens/{citizen_id}/document-uploads")
    assert list_res.json() == []


async def test_non_owner_cannot_access_another_users_documents(client):
    owner = await _login(client, "doc-owner@example.com")
    other = await _login(client, "doc-other@example.com")
    owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    citizen_id = await _make_citizen(client, headers=owner_headers)
    await client.post(
        f"/api/citizens/{citizen_id}/document-uploads",
        json={"document_type": "Aadhaar Card", "filename": "aadhaar.pdf", "content_type": "application/pdf", "file_base64": SAMPLE_B64},
        headers=owner_headers,
    )

    forbidden_res = await client.get(f"/api/citizens/{citizen_id}/document-uploads", headers=other_headers)
    assert forbidden_res.status_code == 403

    allowed_res = await client.get(f"/api/citizens/{citizen_id}/document-uploads", headers=owner_headers)
    assert allowed_res.status_code == 200


async def test_unknown_citizen_returns_404(client):
    res = await client.post(
        "/api/citizens/000000000000000000000000/document-uploads",
        json={"document_type": "Aadhaar Card", "filename": "x.pdf", "content_type": "application/pdf", "file_base64": SAMPLE_B64},
    )
    assert res.status_code == 404
