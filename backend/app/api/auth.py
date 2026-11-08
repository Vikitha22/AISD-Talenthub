from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BRANCHES, INTERVIEW_MODES, JOB_TYPES, ROUND_TYPES
from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.schemas.schemas import LoginRequest
from app.services.auth_service import AuthService

router = APIRouter(tags=["auth"])


@router.post("/auth/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService.login(db, payload.email, payload.password)


@router.get("/auth/me")
async def me(user: CurrentUser = Depends(get_current_user)):
    return {"user_id": user.id, "role": user.role, "linked_id": user.linked_id, "name": user.name}


@router.get("/meta")
async def meta():
    """Option lists used by the forms (so the UI and the validation never disagree)."""
    return {"branches": BRANCHES, "job_types": JOB_TYPES, "round_types": ROUND_TYPES, "interview_modes": INTERVIEW_MODES}
