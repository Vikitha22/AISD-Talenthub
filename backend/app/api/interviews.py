from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, require_role
from app.schemas.schemas import InterviewRescheduleRequest, InterviewResultRequest, InterviewScheduleRequest
from app.services.interview_service import InterviewService
from app.services.serializers import serialize_application

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("/schedule")
async def schedule_interview(body: InterviewScheduleRequest, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(require_role("COMPANY"))):
    return serialize_application(await InterviewService.schedule(db, user.linked_id, body), "COMPANY")


@router.patch("/{interview_id}/reschedule")
async def reschedule_interview(
    interview_id: int, body: InterviewRescheduleRequest, db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("COMPANY")),
):
    return serialize_application(await InterviewService.reschedule(db, user.linked_id, interview_id, body), "COMPANY")


@router.patch("/{interview_id}/result")
async def record_result(
    interview_id: int, body: InterviewResultRequest, db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("COMPANY")),
):
    if not body.confirm_completed:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Confirm that the scheduled interview actually took place before recording a result.")
    app = await InterviewService.record_result(db, user.linked_id, interview_id, body.result, body.feedback)
    return serialize_application(app, "COMPANY")
