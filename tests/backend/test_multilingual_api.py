"""API tests for /api/language/* — no GEMINI_API_KEY in the test env, so both endpoints take
their honest no-op path (Section 7.4)."""


async def test_detect_translate_endpoint_passthrough_without_key(client):
    res = await client.post("/api/language/detect-translate", json={"text": "hello there"})
    assert res.status_code == 200
    body = res.json()
    assert body["detected_language"] == "en"
    assert body["translated_text"] == "hello there"


async def test_translate_response_endpoint_passthrough_without_key(client):
    res = await client.post(
        "/api/language/translate-response",
        json={"text": "You are eligible.", "target_language": "Hindi", "critical_values": []},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["translated"] is False
    assert body["text"] == "You are eligible."
