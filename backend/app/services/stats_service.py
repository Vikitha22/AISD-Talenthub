from sqlalchemy.ext.asyncio import AsyncSession

from app.core import constants as C
from app.core.timeutil import iso, utcnow
from app.repositories.repository import (
    ApplicationRepository,
    CompanyRepository,
    JobRepository,
    PolicyRepository,
    StudentRepository,
)
from app.services.offer_service import OfferService


class StatsService:
    @staticmethod
    async def overview(db: AsyncSession) -> dict:
        await OfferService.expire_overdue(db)
        students = await StudentRepository.list_all(db)
        companies = await CompanyRepository.list_all(db)
        jobs = await JobRepository.list_all(db)
        apps = await ApplicationRepository.list_all(db)
        now = utcnow()

        accepted = [a for a in apps if a.status == C.ACCEPTED and a.offer]
        placed_ids = {a.student_id for a in accepted}
        offers = [a.offer for a in apps if a.offer]
        packages = [o.package_lpa for o in (a.offer for a in accepted)]

        by_branch = []
        for branch in sorted({s.branch for s in students}):
            group = [s for s in students if s.branch == branch]
            placed = sum(1 for s in group if s.id in placed_ids)
            by_branch.append({
                "branch": branch, "students": len(group), "placed": placed,
                "percentage": round(placed / len(group) * 100, 1) if group else 0.0,
            })

        by_company = []
        for c in companies:
            c_apps = [a for a in apps if a.job.company_id == c.id]
            by_company.append({
                "company": c.name,
                "jobs": sum(1 for j in jobs if j.company_id == c.id),
                "applications": len(c_apps),
                "offers": sum(1 for a in c_apps if a.offer),
                "accepted": sum(1 for a in c_apps if a.status == C.ACCEPTED),
            })

        status_breakdown: dict[str, int] = {}
        for a in apps:
            status_breakdown[a.status] = status_breakdown.get(a.status, 0) + 1

        policy = await PolicyRepository.get_active(db)
        accepted_policy = len(await PolicyRepository.accepted_student_ids(db, policy.id)) if policy else 0

        return {
            "total_students": len(students),
            "placed_students": len(placed_ids),
            "unplaced_students": len(students) - len(placed_ids),
            "placement_percentage": round(len(placed_ids) / len(students) * 100, 1) if students else 0.0,
            "total_companies": len(companies),
            "total_jobs": len(jobs),
            "open_jobs": sum(1 for j in jobs if j.deadline > now),
            "total_applications": len(apps),
            "rejected_applications": status_breakdown.get(C.REJECTED, 0),
            "offers_issued": len(offers),
            "offers_pending": sum(1 for o in offers if o.status == C.OFFER_PENDING),
            "offers_accepted": sum(1 for o in offers if o.status == C.OFFER_ACCEPTED),
            "offers_declined": sum(1 for o in offers if o.status == C.OFFER_DECLINED),
            "offers_expired": sum(1 for o in offers if o.status == C.OFFER_EXPIRED_STATE),
            "average_package_lpa": round(sum(packages) / len(packages), 2) if packages else 0.0,
            "highest_package_lpa": max(packages) if packages else 0.0,
            "policy_version": policy.version if policy else None,
            "policy_accepted_by": accepted_policy,
            "status_breakdown": status_breakdown,
            "by_branch": by_branch,
            "by_company": by_company,
        }

    @staticmethod
    async def students(db: AsyncSession) -> list[dict]:
        students = await StudentRepository.list_all(db)
        apps = await ApplicationRepository.list_all(db)
        policy = await PolicyRepository.get_active(db)
        accepted_ids = await PolicyRepository.accepted_student_ids(db, policy.id) if policy else set()
        out = []
        for s in students:
            mine = [a for a in apps if a.student_id == s.id]
            placed = next((a for a in mine if a.status == C.ACCEPTED), None)
            out.append({
                "id": s.id, "roll_number": s.roll_number, "name": s.name, "email": s.email, "branch": s.branch,
                "cgpa": s.cgpa, "active_backlogs": s.active_backlogs,
                "applications": len(mine),
                "placed": placed is not None,
                "placed_at": placed.job.company.name if placed else None,
                "package_lpa": placed.offer.package_lpa if placed and placed.offer else None,
                "policy_accepted": (policy is None) or s.id in accepted_ids,
            })
        return out

    @staticmethod
    async def audit(db: AsyncSession) -> list[dict]:
        return [
            {"student": s.name, "roll_number": s.roll_number, "field": a.field,
             "old_value": a.old_value, "new_value": a.new_value, "changed_at": iso(a.changed_at)}
            for a, s in await StudentRepository.list_audit(db)
        ]
