from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from app.api.agent import router as agent_router
from app.api.analytics import router as analytics_router
from app.api.assistance import router as assistance_router
from app.api.assistant import router as assistant_router
from app.api.auth import router as auth_router
from app.api.bundle import router as bundle_router
from app.api.catalog import router as catalog_router
from app.api.checklist import router as checklist_router
from app.api.citizens import router as citizens_router
from app.api.conflict_rules import router as conflict_rules_router
from app.api.conflicts import router as conflicts_router
from app.api.document_uploads import router as document_uploads_router
from app.api.document_verification import router as document_verification_router
from app.api.eligibility import router as eligibility_router
from app.api.fraud import router as fraud_router
from app.api.grievances import router as grievances_router
from app.api.health import router as health_router
from app.api.multilingual import router as multilingual_router
from app.api.nl_search import router as nl_search_router
from app.api.notifications import router as notifications_router
from app.api.policy_search import router as policy_search_router
from app.api.quick_check import router as quick_check_router
from app.api.rag_candidates import router as rag_candidates_router
from app.api.reminders import router as reminders_router
from app.api.saved_schemes import router as saved_schemes_router
from app.api.scheme_discovery import router as scheme_discovery_router
from app.api.scheme_reports import router as scheme_reports_router
from app.api.video_recommendation import router as video_recommendation_router
from app.api.voice_intake import router as voice_intake_router
from app.api.web_scheme_search import router as web_scheme_search_router
from app.api.schemes import router as schemes_router
from app.core.config import get_settings
from app.core.db import get_db
from app.modules.scheme_kb.service import seed_schemes_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.seed_schemes_on_startup:
        await seed_schemes_if_empty(get_db())
    yield


app = FastAPI(title="ASBO API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def assistance_cors_middleware(request: Request, call_next):
    """The /api/assistance/* routes must be callable from an arbitrary scheme application
    domain — one that can't live in the static CORS_ORIGINS allowlist above, since it isn't
    known until a curator sets that scheme's application_url (any government site, not ours).
    Reflecting the request's own Origin (never "*") is safe here specifically because these
    routes already independently verify the caller's Origin against the signed
    assistance_token server-side (see require_assistance_session in app/core/auth.py) — this
    middleware only controls whether the extension's JS is allowed to read the response, not
    whether the request itself is authorized.
    """
    origin = request.headers.get("origin")
    if origin and request.url.path.startswith("/api/assistance/"):
        if request.method == "OPTIONS":
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Assistance-Origin",
                    "Access-Control-Max-Age": "600",
                },
            )
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        return response
    return await call_next(request)


app.include_router(health_router, tags=["health"])
app.include_router(auth_router)
app.include_router(citizens_router)
app.include_router(schemes_router)
app.include_router(eligibility_router)
app.include_router(conflicts_router)
app.include_router(conflict_rules_router)
app.include_router(bundle_router)
app.include_router(checklist_router)
app.include_router(agent_router)
app.include_router(policy_search_router)
app.include_router(document_verification_router)
app.include_router(document_uploads_router)
app.include_router(reminders_router)
app.include_router(grievances_router)
app.include_router(fraud_router)
app.include_router(multilingual_router)
app.include_router(assistant_router)
app.include_router(assistance_router)
app.include_router(quick_check_router)
app.include_router(catalog_router)
app.include_router(rag_candidates_router)
app.include_router(scheme_discovery_router)
app.include_router(voice_intake_router)
app.include_router(notifications_router)
app.include_router(saved_schemes_router)
app.include_router(nl_search_router)
app.include_router(analytics_router)
app.include_router(scheme_reports_router)
app.include_router(video_recommendation_router)
app.include_router(web_scheme_search_router)
