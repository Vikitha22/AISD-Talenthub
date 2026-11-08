from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import constants as C
from app.core.timeutil import utcnow
from app.models.models import Application
from app.repositories.repository import (
    ApplicationRepository,
    JobRepository,
    PolicyRepository,
    StudentRepository,
)
from app.services.eligibility_service import EligibilityService
from app.services.offer_service import OfferService
from app.services.workflow import set_status


def bad_request(message: str, reasons: list[str] | None = None, code: str | None = None) -> HTTPException:
    return HTTPException(status_code=400, detail={"message": message, "reasons": reasons or [], "code": code})


async def get_owned_application(db: AsyncSession, company_id: int, application_id: int) -> Application:
    """Company-scoped lookup. Unknown id and someone else's id give the same answer (no information leak)."""
    application = await ApplicationRepository.get(db, application_id)
    if not application or application.job.company_id != company_id:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


class ApplicationService:
    @staticmethod
    async def apply(db: AsyncSession, student_id: int, job_id: int) -> Application:
        student = await StudentRepository.get(db, student_id)
        job = await JobRepository.get(db, job_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student profile not found")
        if not job:
            raise HTTPException(status_code=404, detail="Job listing not found")

        policy = await PolicyRepository.get_active(db)
        if policy and not await PolicyRepository.get_acceptance(db, student_id, policy.id):
            raise bad_request(
                "Read and accept the active Placement Policy before applying to any job.",
                ["Placement Policy acceptance is required once before your first application."],
                code="POLICY_NOT_ACCEPTED",
            )
        blockers = EligibilityService.application_blockers(
            student,
            job,
            now=utcnow(),
            already_applied=await ApplicationRepository.get_existing(db, student_id, job_id) is not None,
            placed=await ApplicationRepository.student_has_status(db, student_id, C.ACCEPTED),
            policy_accepted=True,
            policy_version=policy.version if policy else None,
        )
        if blockers:
            raise bad_request(
                "You cannot apply to this job.", [m for _, m in blockers], code=blockers[0][0]
            )

        application = Application(
            student_id=student_id, job_id=job_id, status=C.APPLIED,
            policy_id=policy.id if policy else None,
        )
        ApplicationRepository.add(db, application)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise bad_request("You have already applied to this job.", code="ALREADY_APPLIED")
        set_status(
            db,
            application,
            C.APPLIED,
            "Application submitted. All eligibility checks passed"
            + ".",
            "STUDENT",
        )
        await db.commit()
        return await ApplicationRepository.get(db, application.id)

    @staticmethod
    async def review(
        db: AsyncSession, company_id: int, application_id: int, status: str, reason: str | None, note: str | None
    ) -> Application:
        application = await get_owned_application(db, company_id, application_id)

        if status == C.SHORTLISTED:
            if application.status != C.APPLIED:
                raise bad_request(f"Only applications in APPLIED status can be shortlisted (this one is {application.status}).")
            reasons = EligibilityService.academic_reasons(application.student, application.job)
            if reasons:
                raise bad_request(
                    "The student's current profile no longer meets this job's criteria, so they cannot be shortlisted.",
                    reasons,
                    code="NOT_ELIGIBLE",
                )
            set_status(db, application, C.SHORTLISTED, (note or "").strip() or "Shortlisted by the company.", "COMPANY")

        else:  # REJECTED
            if application.status not in C.OPEN_STATUSES:
                raise bad_request(f"An application in {application.status} status can no longer be rejected.")
            reason = (reason or "").strip()
            if len(reason) < 5:
                raise bad_request("A reason (at least 5 characters) is required when rejecting an application.", code="REASON_REQUIRED")
            application.rejection_reason = reason
            set_status(db, application, C.REJECTED, f"Rejected by the company: {reason}", "COMPANY")

        await db.commit()
        return await ApplicationRepository.get(db, application_id)

    @staticmethod
    async def complete_selection(db: AsyncSession, company_id: int, application_id: int) -> Application:
        """Record the company's final selection decision without managing interview calendars."""
        application = await get_owned_application(db, company_id, application_id)
        if application.status != C.SHORTLISTED:
            raise bad_request(
                f"The selection process can only be completed for SHORTLISTED applications (this one is {application.status})."
            )
        set_status(
            db, application, C.INTERVIEW_CLEARED,
            "Company marked the published selection process as completed successfully.", "COMPANY"
        )
        await db.commit()
        return await ApplicationRepository.get(db, application_id)

    # ---- read side -------------------------------------------------------------------------------------------
    @staticmethod
    async def list_for_student(db: AsyncSession, student_id: int):
        await OfferService.expire_overdue(db)
        return await ApplicationRepository.list_by_student(db, student_id)

    @staticmethod
    async def list_for_company(db: AsyncSession, company_id: int):
        await OfferService.expire_overdue(db)
        return await ApplicationRepository.list_by_company(db, company_id)

    @staticmethod
    async def list_for_job(db: AsyncSession, job_id: int, company_id: int | None):
        await OfferService.expire_overdue(db)
        job = await JobRepository.get(db, job_id)
        if not job or (company_id is not None and job.company_id != company_id):
            raise HTTPException(status_code=404, detail="Job listing not found")
        return await ApplicationRepository.list_by_job(db, job_id)

    @staticmethod
    async def list_all(db: AsyncSession):
        await OfferService.expire_overdue(db)
        return await ApplicationRepository.list_all(db)
