from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models.auth import (
    LoginRequest,
    LoginStep1Response,
    RegisterRequest,
    TokenResponse,
    UserOut,
    VerifyOtpRequest,
)
from app.modules.auth import service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: RegisterRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.register_user(db, payload)


@router.post("/login", response_model=LoginStep1Response)
async def login(payload: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    pending_token, debug_otp = await service.login_step1(db, payload.email, payload.password)
    return LoginStep1Response(pending_token=pending_token, debug_otp=debug_otp)


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(payload: VerifyOtpRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await service.verify_otp(db, payload.pending_token, payload.code)


@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)):
    return current_user
