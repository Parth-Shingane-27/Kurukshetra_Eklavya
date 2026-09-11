from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agent import router as agent_router
from app.api.assistant import router as assistant_router
from app.api.bundle import router as bundle_router
from app.api.checklist import router as checklist_router
from app.api.citizens import router as citizens_router
from app.api.conflict_rules import router as conflict_rules_router
from app.api.conflicts import router as conflicts_router
from app.api.document_verification import router as document_verification_router
from app.api.eligibility import router as eligibility_router
from app.api.fraud import router as fraud_router
from app.api.grievances import router as grievances_router
from app.api.health import router as health_router
from app.api.multilingual import router as multilingual_router
from app.api.policy_search import router as policy_search_router
from app.api.reminders import router as reminders_router
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

app.include_router(health_router, tags=["health"])
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
app.include_router(reminders_router)
app.include_router(grievances_router)
app.include_router(fraud_router)
app.include_router(multilingual_router)
app.include_router(assistant_router)
