from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, require_role
from app.schemas.schemas import JobCreate
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
async def list_jobs(db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(require_role("STUDENT", "COORDINATOR", "COMPANY"))):
    """Students get each job together with a live eligibility verdict and the exact reasons."""
    if user.role == "STUDENT":
        return await JobService.list_for_student(db, user.linked_id)
    return await JobService.list_all(db)


@router.get("/mine")
async def my_jobs(db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(require_role("COMPANY"))):
    return await JobService.list_mine(db, user.linked_id)


@router.post("")
async def create_job(body: JobCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(require_role("COMPANY"))):
    return await JobService.create(db, user.linked_id, body)


@router.get("/{job_id}")
async def get_job(job_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_role("STUDENT", "COORDINATOR", "COMPANY"))):
    return await JobService.get(db, job_id)
