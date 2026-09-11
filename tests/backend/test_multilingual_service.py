"""Multi-language Chat Agent tests (Section 7.4). No real network calls — LangChain's
ChatGoogleGenerativeAI and the plain call_gemini helper are both mocked, same convention as
the existing Explanation Agent tests."""

from app.modules.multilingual.schemas import DetectAndTranslate
from app.modules.multilingual.service import detect_and_translate_to_english, translate_response


async def test_detect_translate_no_key_assumes_english_passthrough():
    result = await detect_and_translate_to_english("hello", api_key=None, model="gemini-flash-latest")
    assert result.detected_language == "en"
    assert result.translated_text == "hello"


async def test_detect_translate_empty_text_short_circuits():
    result = await detect_and_translate_to_english("   ", api_key="fake-key", model="gemini-flash-latest")
    assert result.translated_text == "   "


async def test_detect_translate_uses_structured_llm_output(monkeypatch):
    class FakeStructuredLLM:
        async def ainvoke(self, prompt):
            return DetectAndTranslate(detected_language="Hindi", translated_text="Tell me about PM-KISAN.")

    class FakeChatModel:
        def __init__(self, **kwargs):
            pass

        def with_structured_output(self, schema):
            return FakeStructuredLLM()

    monkeypatch.setattr("app.modules.multilingual.service.ChatGoogleGenerativeAI", FakeChatModel)
    result = await detect_and_translate_to_english(
        "मुझे पीएम-किसान के बारे में बताओ", api_key="fake-key", model="gemini-flash-latest"
    )
    assert result.detected_language == "Hindi"
    assert result.translated_text == "Tell me about PM-KISAN."


async def test_detect_translate_falls_back_on_llm_failure(monkeypatch):
    class FakeChatModel:
        def __init__(self, **kwargs):
            raise RuntimeError("network down")

    monkeypatch.setattr("app.modules.multilingual.service.ChatGoogleGenerativeAI", FakeChatModel)
    result = await detect_and_translate_to_english("some text", api_key="fake-key", model="gemini-flash-latest")
    assert result.detected_language == "unknown"
    assert result.translated_text == "some text"


async def test_translate_response_skips_when_target_is_english():
    result = await translate_response("Hello", "en", [], api_key="fake-key", model="m")
    assert result == {"text": "Hello", "translated": False, "warning": None}


async def test_translate_response_skips_when_no_api_key():
    result = await translate_response("Hello", "Hindi", [], api_key=None, model="m")
    assert result["translated"] is False


async def test_translate_response_succeeds_when_critical_values_preserved(monkeypatch):
    async def fake_call_gemini(prompt, api_key, model):
        return "आपको PM-KISAN योजना के लिए 6000 रुपये मिलेंगे।"

    monkeypatch.setattr("app.modules.multilingual.service.call_gemini", fake_call_gemini)
    result = await translate_response(
        "You are eligible for PM-KISAN, benefit 6000.", "Hindi",
        critical_values=["PM-KISAN", "6000"], api_key="fake-key", model="m",
    )
    assert result["translated"] is True
    assert result["warning"] is None
    assert "PM-KISAN" in result["text"]


async def test_translate_response_falls_back_when_critical_value_dropped(monkeypatch):
    async def fake_call_gemini(prompt, api_key, model):
        return "आपको एक योजना के लिए पैसे मिलेंगे।"  # scheme name/amount dropped

    monkeypatch.setattr("app.modules.multilingual.service.call_gemini", fake_call_gemini)
    result = await translate_response(
        "You are eligible for PM-KISAN, benefit 6000.", "Hindi",
        critical_values=["PM-KISAN", "6000"], api_key="fake-key", model="m",
    )
    assert result["translated"] is False
    assert result["text"] == "You are eligible for PM-KISAN, benefit 6000."
    assert "guard failed" in result["warning"]


async def test_translate_response_falls_back_on_llm_failure(monkeypatch):
    async def fake_call_gemini(prompt, api_key, model):
        raise RuntimeError("network down")

    monkeypatch.setattr("app.modules.multilingual.service.call_gemini", fake_call_gemini)
    result = await translate_response("Hello", "Hindi", [], api_key="fake-key", model="m")
    assert result["translated"] is False
    assert result["text"] == "Hello"
