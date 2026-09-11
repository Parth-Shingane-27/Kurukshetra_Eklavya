from fastapi import APIRouter

from app.core.config import get_settings
from app.models.multilingual import (
    DetectAndTranslateOut,
    DetectAndTranslateRequest,
    TranslateResponseOut,
    TranslateResponseRequest,
)
from app.modules.multilingual import service

router = APIRouter(prefix="/api/language", tags=["multilingual"])


@router.post("/detect-translate", response_model=DetectAndTranslateOut)
async def detect_translate(payload: DetectAndTranslateRequest):
    settings = get_settings()
    result = await service.detect_and_translate_to_english(
        payload.text, settings.gemini_api_key, settings.gemini_model
    )
    return DetectAndTranslateOut(**result.model_dump())


@router.post("/translate-response", response_model=TranslateResponseOut)
async def translate_response(payload: TranslateResponseRequest):
    settings = get_settings()
    result = await service.translate_response(
        payload.text, payload.target_language, payload.critical_values,
        settings.gemini_api_key, settings.gemini_model,
    )
    return TranslateResponseOut(**result)
