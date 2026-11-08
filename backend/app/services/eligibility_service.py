from datetime import datetime

from app.models.models import JobListing, Student


def split_branches(value: str) -> list[str]:
    return [] if value == "*" else [b for b in (value or "").split(",") if b]


class EligibilityService:
    """Pure rule checks - no database access, easy to unit-test."""

    @staticmethod
    def academic_reasons(student: Student, job: JobListing) -> list[str]:
        """Why the student's academic profile does not meet the job's criteria (empty = meets all)."""
        reasons: list[str] = []
        if student.cgpa < job.min_cgpa:
            reasons.append(f"CGPA {student.cgpa:g} is below the required minimum of {job.min_cgpa:g}")
        if student.active_backlogs > job.max_backlogs:
            reasons.append(
                f"{student.active_backlogs} active backlog(s) exceed the maximum allowed ({job.max_backlogs})"
            )
        branches = split_branches(job.allowed_branches)
        if branches and student.branch not in branches:
            reasons.append(f"Branch '{student.branch}' is not eligible (open to: {', '.join(branches)})")
        return reasons

    @staticmethod
    def application_blockers(
        student: Student,
        job: JobListing,
        *,
        now: datetime,
        already_applied: bool,
        placed: bool,
        policy_accepted: bool = True,
        policy_version: int | None = None,
    ) -> list[tuple[str, str]]:
        """Everything that currently stops this student applying, as (code, human message) pairs."""
        blockers: list[tuple[str, str]] = []
        if job.deadline <= now:
            blockers.append(("DEADLINE_PASSED", "The application deadline has passed"))
        if already_applied:
            blockers.append(("ALREADY_APPLIED", "You have already applied to this job"))
        if placed:
            blockers.append(("ALREADY_PLACED", "You have already accepted an offer, so you cannot apply to more jobs"))
        for r in EligibilityService.academic_reasons(student, job):
            blockers.append(("NOT_ELIGIBLE", r))
        return blockers
