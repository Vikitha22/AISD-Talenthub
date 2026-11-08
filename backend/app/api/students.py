from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, require_role
from app.repositories.repository import StudentRepository
from app.schemas.schemas import ProfileUpdate, AcademicUpdateRequestSchema
from app.services.profile_service import ProfileService
from app.services.serializers import serialize_student

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/me")
async def my_profile(db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(require_role("STUDENT"))):
    student = await StudentRepository.get(db, user.linked_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return serialize_student(student)


@router.patch("/me")
async def update_my_profile(
    body: ProfileUpdate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(require_role("STUDENT"))
):
    student = await ProfileService.update(db, user.linked_id, body.model_dump(exclude_unset=True))
    return serialize_student(student)


@router.post("/me/academic-update-requests")
async def request_academic_update(body: AcademicUpdateRequestSchema, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(require_role("STUDENT"))):
    req = await ProfileService.request_academic_update(db, user.linked_id, body.field, body.value)
    return {"id": req.id, "field": req.field, "old_value": req.old_value, "requested_value": req.requested_value, "status": req.status}


@router.get("/me/academic-update-requests")
async def my_academic_update_requests(db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(require_role("STUDENT"))):
    rows = (await db.execute(select(AcademicUpdateRequest).where(AcademicUpdateRequest.student_id == user.linked_id).order_by(AcademicUpdateRequest.created_at.desc()))).scalars().all()
    return [{"id": r.id, "field": r.field, "old_value": r.old_value, "requested_value": r.requested_value, "status": r.status, "coordinator_note": r.coordinator_note, "created_at": r.created_at.isoformat()} for r in rows]
