from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import constants as C
from app.core.timeutil import utcnow
from app.models.models import JobListing
from app.repositories.repository import (
    ApplicationRepository,
    JobRepository,
    PolicyRepository,
    StudentRepository,
)
from app.services.eligibility_service import EligibilityService
from app.services.serializers import serialize_job


class JobService:
    @staticmethod
    async def list_for_student(db: AsyncSession, student_id: int) -> list[dict]:
        student = await StudentRepository.get(db, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student profile not found")
        placed = await ApplicationRepository.student_has_status(db, student_id, C.ACCEPTED)
        applied = {a.job_id: a.id for a in await ApplicationRepository.list_by_student(db, student_id)}
        now = utcnow()
        out = []
        for job in await JobRepository.list_all(db):
            blockers = EligibilityService.application_blockers(
                student, job, now=now, already_applied=job.id in applied, placed=placed,
                policy_accepted=True, policy_version=None,
            )
            academic = EligibilityService.academic_reasons(student, job)
            out.append(
                serialize_job(
                    job,
                    student_ctx={
                        "eligible": not academic,           # meets CGPA / backlog / branch criteria
                        "can_apply": not blockers,          # eligible AND open AND policy accepted AND not applied
                        "applied": job.id in applied,
                        "application_id": applied.get(job.id),
                        "reasons": [m for _, m in blockers],
                        "blocker_codes": [c for c, _ in blockers],
                    },
                )
            )
        return out

    @staticmethod
    async def list_all(db: AsyncSession) -> list[dict]:
        return [serialize_job(j, include_counts=True) for j in await JobRepository.list_all(db)]

    @staticmethod
    async def list_mine(db: AsyncSession, company_id: int) -> list[dict]:
        return [serialize_job(j, include_counts=True) for j in await JobRepository.list_by_company(db, company_id)]

    @staticmethod
    async def get(db: AsyncSession, job_id: int) -> dict:
        job = await JobRepository.get(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job listing not found")
        return serialize_job(job)

    @staticmethod
    async def create(db: AsyncSession, company_id: int, body) -> dict:
        if body.deadline <= utcnow():
            raise HTTPException(
                status_code=400,
                detail={"message": "The application deadline must be in the future.", "reasons": [], "code": "BAD_DEADLINE"},
            )
        data = body.model_dump()
        data["allowed_branches"] = "*" if data.pop("all_branches", False) else ",".join(data["allowed_branches"])
        import json
        data["selection_rounds"] = json.dumps(data.get("selection_rounds", []))
        job = JobListing(company_id=company_id, **data)
        JobRepository.add(db, job)
        await db.commit()
        return serialize_job(await JobRepository.get(db, job.id), include_counts=True)
