"""FR-012 — Multilingual Conversational & Voice Profile Intake (BR-013: no separate
validation/persistence path from the structured form)."""

from app.models.voice_intake import ExtractedProfileSlots, SlotExtractionDraft
from app.modules.multilingual.schemas import DetectAndTranslate
from app.modules.voice_intake import service


class _FakeSettingsWithKey:
    gemini_api_key = "fake-key"
    gemini_model = "gemini-2.0-flash"


class _FakeSettingsNoKey:
    gemini_api_key = None
    gemini_model = "gemini-2.0-flash"


class _FakeStructuredLLM:
    def __init__(self, draft=None, raise_error=False):
        self._draft = draft
        self._raise_error = raise_error

    async def ainvoke(self, prompt):
        if self._raise_error:
            raise RuntimeError("simulated LLM failure")
        return self._draft


class _FakeChatModel:
    def __init__(self, draft=None, raise_error=False):
        self._draft = draft
        self._raise_error = raise_error

    def with_structured_output(self, schema):
        return _FakeStructuredLLM(self._draft, self._raise_error)


def _chat_model_factory(draft=None, raise_error=False):
    def factory(model, google_api_key):
        return _FakeChatModel(draft, raise_error)
    return factory


async def _passthrough_detect(text, api_key, model):
    return DetectAndTranslate(detected_language="en", translated_text=text)


async def _passthrough_translate(text, target_language, critical_values, api_key, model):
    return {"text": text, "translated": False, "warning": None}


def _patch_multilingual_passthrough(monkeypatch):
    monkeypatch.setattr(service, "detect_and_translate_to_english", _passthrough_detect)
    monkeypatch.setattr(service, "translate_response", _passthrough_translate)


async def test_no_gemini_key_falls_back_to_structured_form_message(client, db, monkeypatch):
    _patch_multilingual_passthrough(monkeypatch)
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsNoKey())

    res = await client.post("/api/intake/converse", json={"transcript": "My name is Asha"})
    assert res.status_code == 200
    body = res.json()
    assert body["is_complete"] is False
    assert body["citizen_id"] is None
    assert "structured form" in body["assistant_message"]


async def test_extraction_failure_falls_back_to_next_mandatory_field_question(client, db, monkeypatch):
    _patch_multilingual_passthrough(monkeypatch)
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsWithKey())
    monkeypatch.setattr(service, "ChatGoogleGenerativeAI", _chat_model_factory(raise_error=True))

    res = await client.post("/api/intake/converse", json={"transcript": "Hello"})
    assert res.status_code == 200
    body = res.json()
    assert body["is_complete"] is False
    assert "full name" in body["assistant_message"]


async def test_slots_accumulate_across_turns_and_create_citizen_on_completion(client, db, monkeypatch):
    _patch_multilingual_passthrough(monkeypatch)
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsWithKey())

    draft1 = SlotExtractionDraft(
        extracted=ExtractedProfileSlots(name="Asha Patil"),
        follow_up_question_en="What is your date of birth?",
    )
    monkeypatch.setattr(service, "ChatGoogleGenerativeAI", _chat_model_factory(draft=draft1))
    res1 = await client.post("/api/intake/converse", json={"transcript": "My name is Asha Patil"})
    body1 = res1.json()
    session_id = body1["session_id"]
    assert body1["collected_profile"]["name"] == "Asha Patil"
    assert body1["is_complete"] is False
    assert body1["citizen_id"] is None

    draft2 = SlotExtractionDraft(
        extracted=ExtractedProfileSlots(
            date_of_birth="2001-05-10", state="Maharashtra", district="Pune"
        ),
        follow_up_question_en=None,
    )
    monkeypatch.setattr(service, "ChatGoogleGenerativeAI", _chat_model_factory(draft=draft2))
    res2 = await client.post(
        "/api/intake/converse",
        json={"transcript": "10 May 2001, Pune, Maharashtra", "session_id": session_id},
    )
    body2 = res2.json()
    assert body2["session_id"] == session_id
    assert body2["is_complete"] is True
    assert body2["citizen_id"] is not None

    citizen_res = await client.get(f"/api/citizens/{body2['citizen_id']}")
    assert citizen_res.status_code == 200
    citizen = citizen_res.json()
    assert citizen["name"] == "Asha Patil"
    assert citizen["state"] == "Maharashtra"
    assert citizen["district"] == "Pune"
    assert citizen["date_of_birth"] == "2001-05-10"


async def test_invalid_extracted_value_is_rejected_not_silently_accepted(client, db, monkeypatch):
    _patch_multilingual_passthrough(monkeypatch)
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsWithKey())

    draft = SlotExtractionDraft(
        extracted=ExtractedProfileSlots(date_of_birth="not-a-real-date"),
        follow_up_question_en="Could you repeat your date of birth?",
    )
    monkeypatch.setattr(service, "ChatGoogleGenerativeAI", _chat_model_factory(draft=draft))

    res = await client.post("/api/intake/converse", json={"transcript": "I was born sometime"})
    body = res.json()
    assert "date_of_birth" in body["rejected_fields"]
    assert "date_of_birth" not in body["collected_profile"]
    assert body["is_complete"] is False


async def test_repeat_call_after_completion_returns_same_citizen_without_duplicating(client, db, monkeypatch):
    _patch_multilingual_passthrough(monkeypatch)
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsWithKey())

    draft = SlotExtractionDraft(
        extracted=ExtractedProfileSlots(
            name="Ravi Kumar", date_of_birth="1990-01-01", state="Bihar", district="Patna"
        ),
        follow_up_question_en=None,
    )
    monkeypatch.setattr(service, "ChatGoogleGenerativeAI", _chat_model_factory(draft=draft))

    res1 = await client.post("/api/intake/converse", json={"transcript": "All my details at once"})
    body1 = res1.json()
    session_id = body1["session_id"]
    citizen_id = body1["citizen_id"]
    assert citizen_id is not None

    before_count = await db.citizens.count_documents({})
    res2 = await client.post(
        "/api/intake/converse", json={"transcript": "Anything else?", "session_id": session_id}
    )
    body2 = res2.json()
    after_count = await db.citizens.count_documents({})

    assert body2["citizen_id"] == citizen_id
    assert after_count == before_count


async def test_converse_requires_no_auth(client, db, monkeypatch):
    _patch_multilingual_passthrough(monkeypatch)
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettingsNoKey())

    res = await client.post("/api/intake/converse", json={"transcript": "hello"})
    assert res.status_code == 200
