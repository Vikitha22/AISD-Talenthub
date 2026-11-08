from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, require_role
from app.schemas.schemas import ApplicationCreate, ApplicationStatusUpdate
from app.services.application_service import ApplicationService
from app.services.serializers import serialize_application

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("")
async def apply(body: ApplicationCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(require_role("STUDENT"))):
    return serialize_application(await ApplicationService.apply(db, user.linked_id, body.job_id), "STUDENT")


@router.get("/me")
async def my_applications(db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(require_role("STUDENT"))):
    return [serialize_application(a, "STUDENT") for a in await ApplicationService.list_for_student(db, user.linked_id)]


@router.get("/company/mine")
async def my_company_applications(db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(require_role("COMPANY"))):
    return [serialize_application(a, "COMPANY") for a in await ApplicationService.list_for_company(db, user.linked_id)]


@router.get("/job/{job_id}")
async def applications_for_job(
    job_id: int, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(require_role("COMPANY", "COORDINATOR"))
):
    company_id = user.linked_id if user.role == "COMPANY" else None
    return [serialize_application(a, user.role) for a in await ApplicationService.list_for_job(db, job_id, company_id)]


@router.patch("/{application_id}/status")
async def update_status(
    application_id: int, body: ApplicationStatusUpdate, db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("COMPANY")),
):
    app = await ApplicationService.review(db, user.linked_id, application_id, body.status, body.reason, body.note)
    return serialize_application(app, "COMPANY")


@router.patch("/{application_id}/selection-complete")
async def complete_selection_process(
    application_id: int, db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("COMPANY")),
):
    app = await ApplicationService.complete_selection(db, user.linked_id, application_id)
    return serialize_application(app, "COMPANY")
