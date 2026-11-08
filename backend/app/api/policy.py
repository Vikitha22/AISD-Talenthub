from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user, require_role
from app.repositories.repository import PolicyRepository
from app.schemas.schemas import PolicyAcceptRequest, PolicyPublish
from app.services.policy_service import PolicyService
from app.services.serializers import serialize_policy
from app.core.timeutil import iso

router = APIRouter(prefix="/policy", tags=["policy"])


def _status(s: dict) -> dict:
    return {"policy": serialize_policy(s["policy"]), "accepted": s["accepted"], "accepted_at": iso(s["accepted_at"])}


@router.get("/active")
async def active_policy(db: AsyncSession = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    return serialize_policy(await PolicyRepository.get_active(db))


@router.get("/me")
async def my_policy_status(db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(require_role("STUDENT"))):
    return _status(await PolicyService.status_for_student(db, user.linked_id))


@router.post("/accept")
async def accept_policy(body: PolicyAcceptRequest, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(require_role("STUDENT"))):
    return _status(await PolicyService.accept(db, user.linked_id, body.policy_id, body.agree))


@router.get("/history")
async def policy_history(db: AsyncSession = Depends(get_db), _=Depends(require_role("COORDINATOR"))):
    return [{**serialize_policy(r["policy"]), "acceptances": r["acceptances"]} for r in await PolicyService.list_all(db)]


@router.post("")
async def publish_policy(body: PolicyPublish, db: AsyncSession = Depends(get_db), _=Depends(require_role("COORDINATOR"))):
    return serialize_policy(await PolicyService.publish(db, body.title, body.content))
