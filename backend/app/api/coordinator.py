from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_role
from app.services.application_service import ApplicationService
from app.services.serializers import serialize_application
from app.services.stats_service import StatsService
from app.services.profile_service import ProfileService
from app.schemas.schemas import AcademicReviewRequest

router = APIRouter(prefix="/coordinator", tags=["coordinator"])


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db), _=Depends(require_role("COORDINATOR"))):
    return await StatsService.overview(db)


@router.get("/applications")
async def all_applications(db: AsyncSession = Depends(get_db), _=Depends(require_role("COORDINATOR"))):
    return [serialize_application(a, "COORDINATOR") for a in await ApplicationService.list_all(db)]


@router.get("/students")
async def students(db: AsyncSession = Depends(get_db), _=Depends(require_role("COORDINATOR"))):
    return await StatsService.students(db)


@router.get("/audit")
async def profile_audit(db: AsyncSession = Depends(get_db), _=Depends(require_role("COORDINATOR"))):
    return await StatsService.audit(db)


@router.get("/academic-update-requests")
async def academic_update_requests(db: AsyncSession = Depends(get_db), _=Depends(require_role("COORDINATOR"))):
    return await ProfileService.list_requests(db)

@router.patch("/academic-update-requests/{request_id}")
async def review_academic_update(request_id: int, body: AcademicReviewRequest, db: AsyncSession = Depends(get_db), _=Depends(require_role("COORDINATOR"))):
    return await ProfileService.review_request(db, request_id, body.decision, body.note)
