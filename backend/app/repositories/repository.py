"""Repository layer: the only place that talks to the database.
Repositories never commit - the service that owns the business operation commits once,
so every operation (status change + audit event + interview ...) is atomic."""
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import CANCELLED
from app.models.models import (
    Application,
    ApplicationEvent,
    Company,
    Interview,
    JobListing,
    Offer,
    Policy,
    PolicyAcceptance,
    ProfileAudit,
    Student,
    User,
)


def _application_options():
    return (
        selectinload(Application.student),
        selectinload(Application.job).selectinload(JobListing.company),
        selectinload(Application.interviews),
        selectinload(Application.offer),
        selectinload(Application.events),
    )


class UserRepository:
    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        return (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()

    @staticmethod
    def add(db: AsyncSession, user: User) -> None:
        db.add(user)

    @staticmethod
    async def get_for_student(db: AsyncSession, student_id: int) -> User | None:
        return (await db.execute(select(User).where(User.student_id == student_id))).scalar_one_or_none()


class StudentRepository:
    @staticmethod
    async def get(db: AsyncSession, student_id: int) -> Student | None:
        return await db.get(Student, student_id)

    @staticmethod
    async def list_all(db: AsyncSession) -> list[Student]:
        return list((await db.execute(select(Student).order_by(Student.roll_number))).scalars().all())

    @staticmethod
    def add_audit(db: AsyncSession, row: ProfileAudit) -> None:
        db.add(row)

    @staticmethod
    async def list_audit(db: AsyncSession, limit: int = 200) -> list[tuple[ProfileAudit, Student]]:
        res = await db.execute(
            select(ProfileAudit, Student)
            .join(Student, Student.id == ProfileAudit.student_id)
            .order_by(ProfileAudit.id.desc())
            .limit(limit)
        )
        return [(a, s) for a, s in res.all()]


class CompanyRepository:
    @staticmethod
    async def get(db: AsyncSession, company_id: int) -> Company | None:
        return await db.get(Company, company_id)

    @staticmethod
    async def list_all(db: AsyncSession) -> list[Company]:
        return list((await db.execute(select(Company).order_by(Company.name))).scalars().all())


class JobRepository:
    @staticmethod
    def _q():
        return select(JobListing).options(selectinload(JobListing.company), selectinload(JobListing.applications))

    @staticmethod
    async def get(db: AsyncSession, job_id: int) -> JobListing | None:
        q = JobRepository._q().where(JobListing.id == job_id).execution_options(populate_existing=True)
        return (await db.execute(q)).scalar_one_or_none()

    @staticmethod
    async def list_all(db: AsyncSession) -> list[JobListing]:
        q = JobRepository._q().order_by(JobListing.deadline).execution_options(populate_existing=True)
        return list((await db.execute(q)).scalars().all())

    @staticmethod
    async def list_by_company(db: AsyncSession, company_id: int) -> list[JobListing]:
        q = (
            JobRepository._q()
            .where(JobListing.company_id == company_id)
            .order_by(JobListing.id.desc())
            .execution_options(populate_existing=True)
        )
        return list((await db.execute(q)).scalars().all())

    @staticmethod
    def add(db: AsyncSession, job: JobListing) -> None:
        db.add(job)


class ApplicationRepository:
    @staticmethod
    def _q():
        return select(Application).options(*_application_options()).execution_options(populate_existing=True)

    @staticmethod
    async def get(db: AsyncSession, application_id: int) -> Application | None:
        return (await db.execute(ApplicationRepository._q().where(Application.id == application_id))).scalar_one_or_none()

    @staticmethod
    async def get_existing(db: AsyncSession, student_id: int, job_id: int) -> Application | None:
        q = select(Application).where(Application.student_id == student_id, Application.job_id == job_id)
        return (await db.execute(q)).scalar_one_or_none()

    @staticmethod
    async def list_by_student(db: AsyncSession, student_id: int) -> list[Application]:
        q = ApplicationRepository._q().where(Application.student_id == student_id).order_by(Application.id.desc())
        return list((await db.execute(q)).scalars().all())

    @staticmethod
    async def list_by_job(db: AsyncSession, job_id: int) -> list[Application]:
        q = ApplicationRepository._q().where(Application.job_id == job_id).order_by(Application.id.desc())
        return list((await db.execute(q)).scalars().all())

    @staticmethod
    async def list_by_company(db: AsyncSession, company_id: int) -> list[Application]:
        q = (
            ApplicationRepository._q()
            .join(JobListing, Application.job_id == JobListing.id)
            .where(JobListing.company_id == company_id)
            .order_by(Application.id.desc())
        )
        return list((await db.execute(q)).scalars().all())

    @staticmethod
    async def list_all(db: AsyncSession) -> list[Application]:
        return list((await db.execute(ApplicationRepository._q().order_by(Application.id.desc()))).scalars().all())

    @staticmethod
    async def student_has_status(db: AsyncSession, student_id: int, status: str) -> bool:
        q = select(func.count()).select_from(Application).where(
            Application.student_id == student_id, Application.status == status
        )
        return (await db.execute(q)).scalar_one() > 0

    @staticmethod
    async def list_other_by_student(db: AsyncSession, student_id: int, exclude_id: int) -> list[Application]:
        q = ApplicationRepository._q().where(Application.student_id == student_id, Application.id != exclude_id)
        return list((await db.execute(q)).scalars().all())

    @staticmethod
    def add(db: AsyncSession, application: Application) -> None:
        db.add(application)

    @staticmethod
    def add_event(db: AsyncSession, event: ApplicationEvent) -> None:
        db.add(event)


class InterviewRepository:
    @staticmethod
    async def get(db: AsyncSession, interview_id: int) -> Interview | None:
        q = select(Interview).where(Interview.id == interview_id).execution_options(populate_existing=True)
        return (await db.execute(q)).scalar_one_or_none()

    @staticmethod
    async def list_potential_conflicts(
        db: AsyncSession, company_id: int, student_id: int, venue: str | None, exclude_id: int | None
    ) -> list[tuple[Interview, Application, JobListing]]:
        """Every non-cancelled interview that belongs to the same company, the same student,
        or (for on-campus rounds) the same room - the caller checks the time overlap."""
        cond = [JobListing.company_id == company_id, Application.student_id == student_id]
        if venue:
            cond.append(func.lower(Interview.location) == venue.lower())
        q = (
            select(Interview, Application, JobListing)
            .join(Application, Application.id == Interview.application_id)
            .join(JobListing, JobListing.id == Application.job_id)
            .where(Interview.result != CANCELLED, or_(*cond))
        )
        if exclude_id is not None:
            q = q.where(Interview.id != exclude_id)
        return [(i, a, j) for i, a, j in (await db.execute(q)).all()]

    @staticmethod
    def add(db: AsyncSession, interview: Interview) -> None:
        db.add(interview)


class OfferRepository:
    @staticmethod
    async def get_by_application(db: AsyncSession, application_id: int) -> Offer | None:
        q = select(Offer).where(Offer.application_id == application_id).execution_options(populate_existing=True)
        return (await db.execute(q)).scalar_one_or_none()

    @staticmethod
    async def list_overdue(db: AsyncSession, now: datetime) -> list[Offer]:
        q = select(Offer).where(Offer.status == "PENDING", Offer.respond_by < now)
        return list((await db.execute(q)).scalars().all())

    @staticmethod
    def add(db: AsyncSession, offer: Offer) -> None:
        db.add(offer)


class PolicyRepository:
    @staticmethod
    async def get_active(db: AsyncSession) -> Policy | None:
        q = select(Policy).where(Policy.is_active.is_(True)).order_by(Policy.version.desc())
        return (await db.execute(q)).scalars().first()

    @staticmethod
    async def list_all(db: AsyncSession) -> list[Policy]:
        return list((await db.execute(select(Policy).order_by(Policy.version.desc()))).scalars().all())

    @staticmethod
    async def get(db: AsyncSession, policy_id: int) -> Policy | None:
        return await db.get(Policy, policy_id)

    @staticmethod
    async def max_version(db: AsyncSession) -> int:
        return (await db.execute(select(func.coalesce(func.max(Policy.version), 0)))).scalar_one()

    @staticmethod
    async def get_acceptance(db: AsyncSession, student_id: int, policy_id: int) -> PolicyAcceptance | None:
        q = select(PolicyAcceptance).where(
            PolicyAcceptance.student_id == student_id, PolicyAcceptance.policy_id == policy_id
        )
        return (await db.execute(q)).scalar_one_or_none()

    @staticmethod
    async def count_acceptances(db: AsyncSession, policy_id: int) -> int:
        q = select(func.count()).select_from(PolicyAcceptance).where(PolicyAcceptance.policy_id == policy_id)
        return (await db.execute(q)).scalar_one()

    @staticmethod
    async def accepted_student_ids(db: AsyncSession, policy_id: int) -> set[int]:
        q = select(PolicyAcceptance.student_id).where(PolicyAcceptance.policy_id == policy_id)
        return set((await db.execute(q)).scalars().all())

    @staticmethod
    def add(db: AsyncSession, obj) -> None:
        db.add(obj)
