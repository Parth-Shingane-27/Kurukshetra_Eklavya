"""FR-001, FR-002 — Citizen profile create/retrieve/update/documents (TC-001–005)."""


async def test_create_citizen_valid_profile(client):
    payload = {
        "name": "Asha Devi",
        "date_of_birth": "1985-06-15",
        "state": "Maharashtra",
        "district": "Pune",
        "annual_income": 180000,
        "occupation": "farmer",
        "bpl_status": True,
    }
    res = await client.post("/api/citizens", json=payload)
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "Asha Devi"
    assert body["documents"] == []
    assert "id" in body and "created_at" in body


async def test_create_citizen_missing_required_field_rejected(client):
    # district is required (Section 13) but omitted here.
    payload = {"name": "No District", "date_of_birth": "1990-01-01", "state": "Maharashtra"}
    res = await client.post("/api/citizens", json=payload)
    assert res.status_code == 422


async def test_get_citizen(client):
    create_res = await client.post(
        "/api/citizens",
        json={"name": "Ravi Kumar", "date_of_birth": "1970-01-01", "state": "Bihar", "district": "Patna"},
    )
    citizen_id = create_res.json()["id"]

    res = await client.get(f"/api/citizens/{citizen_id}")
    assert res.status_code == 200
    assert res.json()["name"] == "Ravi Kumar"


async def test_get_citizen_not_found(client):
    res = await client.get("/api/citizens/64b7f0000000000000000000")
    assert res.status_code == 404
    assert res.json()["detail"] == "Profile not found"


async def test_get_citizen_malformed_id(client):
    res = await client.get("/api/citizens/not-an-object-id")
    assert res.status_code == 404


async def test_update_citizen(client):
    create_res = await client.post(
        "/api/citizens",
        json={"name": "Meena", "date_of_birth": "1995-05-05", "state": "Kerala", "district": "Kochi"},
    )
    citizen_id = create_res.json()["id"]

    res = await client.put(f"/api/citizens/{citizen_id}", json={"annual_income": 220000})
    assert res.status_code == 200
    assert res.json()["annual_income"] == 220000
    assert res.json()["name"] == "Meena"  # untouched fields preserved


async def test_update_citizen_not_found(client):
    res = await client.put("/api/citizens/64b7f0000000000000000000", json={"annual_income": 1000})
    assert res.status_code == 404


async def test_declare_documents(client):
    create_res = await client.post(
        "/api/citizens",
        json={"name": "Suresh", "date_of_birth": "1980-01-01", "state": "Odisha", "district": "Cuttack"},
    )
    citizen_id = create_res.json()["id"]

    res = await client.post(
        f"/api/citizens/{citizen_id}/documents",
        json={"documents": [{"document_type": "Aadhaar Card", "held": True}]},
    )
    assert res.status_code == 200
    assert res.json()["documents"] == [{"document_type": "Aadhaar Card", "held": True}]
