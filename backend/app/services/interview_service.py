import asyncio
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import constants as C
from app.core.config import INTERVIEW_MAX_MINUTES, INTERVIEW_MIN_MINUTES
from app.core.timeutil import fmt, utcnow
from app.models.models import Interview
from app.repositories.repository import ApplicationRepository, InterviewRepository
from app.services.application_service import bad_request, get_owned_application
from app.services.workflow import add_note, set_status

# One lock so "check for a clash, then insert" cannot interleave between two simultaneous requests.
_schedule_lock = asyncio.Lock()


def _check_duration(minutes: int) -> None:
    if not (INTERVIEW_MIN_MINUTES <= minutes <= INTERVIEW_MAX_MINUTES):
        raise bad_request(f"Duration must be between {INTERVIEW_MIN_MINUTES} and {INTERVIEW_MAX_MINUTES} minutes.")


def _check_future(when: datetime) -> None:
    if when <= utcnow():
        raise bad_request("The interview must be scheduled for a future date and time.", code="PAST_TIME")


async def _assert_no_clash(
    db: AsyncSession, application, start: datetime, minutes: int, mode: str, location: str, exclude_id: int | None
) -> None:
    """The same slot can never be given to two students (or double-book one student / one room)."""
    end = start + timedelta(minutes=minutes)
    venue = location if mode == "On-campus" else None
    candidates = await InterviewRepository.list_potential_conflicts(
        db, application.job.company_id, application.student_id, venue, exclude_id
    )
    for iv, other_app, other_job in candidates:
        iv_end = iv.scheduled_at + timedelta(minutes=iv.duration_minutes)
        if not (iv.scheduled_at < end and start < iv_end):
            continue
        window = f"{fmt(iv.scheduled_at)} to {fmt(iv_end)}"
        if other_job.company_id == application.job.company_id:
            raise bad_request(
                f"Time slot clash: your company already has an interview in this window ({window}). "
                "Pick a different time.",
                code="SLOT_CLASH",
            )
        if other_app.student_id == application.student_id:
            raise bad_request(
                f"Time slot clash: this student already has another interview in this window ({window}).",
                code="STUDENT_CLASH",
            )
        raise bad_request(
            f"Time slot clash: the venue '{location}' is already booked in this window ({window}).", code="VENUE_CLASH"
        )


class InterviewService:
    @staticmethod
    async def schedule(db: AsyncSession, company_id: int, body) -> object:
        _check_duration(body.duration_minutes)
        _check_future(body.scheduled_at)
        async with _schedule_lock:
            application = await get_owned_application(db, company_id, body.application_id)
            if application.status == C.INTERVIEW_SCHEDULED:
                raise bad_request("A round is already scheduled and its result is still pending. Record that result first.")
            if application.status != C.SHORTLISTED:
                raise bad_request(
                    f"Interviews can only be scheduled for SHORTLISTED applications (this one is {application.status})."
                )
            next_round = len(application.interviews) + 1
            import json
            try:
                published_rounds = json.loads(application.job.selection_rounds or "[]")
            except (TypeError, ValueError):
                published_rounds = []
            if published_rounds and next_round <= len(published_rounds):
                expected = published_rounds[next_round - 1]["name"]
                if body.round_type.strip() != expected:
                    raise bad_request(f"Round {next_round} must use the published round name: {expected}.")
            if next_round > application.job.num_rounds:
                raise bad_request(f"This job has only {application.job.num_rounds} round(s); all have been scheduled.")
            await _assert_no_clash(db, application, body.scheduled_at, body.duration_minutes, body.mode, body.location, None)

            interview = Interview(
                application_id=application.id,
                round_number=next_round,
                round_type=body.round_type,
                mode=body.mode,
                location=body.location,
                scheduled_at=body.scheduled_at,
                duration_minutes=body.duration_minutes,
                notes=body.notes,
            )
            InterviewRepository.add(db, interview)
            set_status(
                db, application, C.INTERVIEW_SCHEDULED,
                f"Round {next_round} of {application.job.num_rounds} ({body.round_type}, {body.mode}) scheduled for "
                f"{fmt(body.scheduled_at)}, {body.duration_minutes} min, at {body.location}.",
                "COMPANY",
            )
            await db.commit()
        return await ApplicationRepository.get(db, application.id)

    @staticmethod
    async def reschedule(db: AsyncSession, company_id: int, interview_id: int, body) -> object:
        if body.duration_minutes is not None:
            _check_duration(body.duration_minutes)
        _check_future(body.scheduled_at)
        async with _schedule_lock:
            interview = await InterviewRepository.get(db, interview_id)
            if not interview:
                raise HTTPException(status_code=404, detail="Interview not found")
            application = await get_owned_application(db, company_id, interview.application_id)
            if interview.result != C.PENDING:
                raise bad_request("Only interviews whose result is still pending can be rescheduled.")
            minutes = body.duration_minutes or interview.duration_minutes
            location = body.location or interview.location
            await _assert_no_clash(db, application, body.scheduled_at, minutes, interview.mode, location, interview.id)
            old = interview.scheduled_at
            interview.scheduled_at = body.scheduled_at
            interview.duration_minutes = minutes
            interview.location = location
            if body.notes is not None:
                interview.notes = body.notes
            add_note(
                db, application,
                f"Round {interview.round_number} rescheduled from {fmt(old)} to {fmt(body.scheduled_at)} (at {location}).",
                "COMPANY",
            )
            await db.commit()
        return await ApplicationRepository.get(db, application.id)

    @staticmethod
    async def record_result(db: AsyncSession, company_id: int, interview_id: int, result: str, feedback: str) -> object:
        interview = await InterviewRepository.get(db, interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        application = await get_owned_application(db, company_id, interview.application_id)
        if interview.result != C.PENDING:
            raise bad_request(f"This round already has a recorded result ({interview.result}); it cannot be changed.")
        if utcnow() < interview.scheduled_at:
            raise bad_request(
                "The interview has not taken place yet. Results can be recorded only after the scheduled date and time.",
                code="INTERVIEW_NOT_COMPLETED",
            )
        if result not in (C.PASS, C.FAIL):
            raise bad_request("Result must be PASS or FAIL.")
        feedback = (feedback or "").strip()
        if result == C.FAIL and len(feedback) < 5:
            raise bad_request("Feedback (at least 5 characters) is required when a student fails a round.", code="REASON_REQUIRED")

        interview.result = result
        interview.feedback = feedback
        n, total = interview.round_number, application.job.num_rounds
        if result == C.FAIL:
            reason = f"Did not clear interview round {n} ({interview.round_type}): {feedback}"
            application.rejection_reason = reason
            set_status(db, application, C.REJECTED, reason, "COMPANY")
        elif n >= total:
            set_status(
                db, application, C.INTERVIEW_CLEARED,
                f"Round {n} of {total} passed - all interview rounds cleared. The company can now issue an offer."
                + (f" Feedback: {feedback}" if feedback else ""),
                "COMPANY",
            )
        else:
            set_status(
                db, application, C.SHORTLISTED,
                f"Round {n} of {total} passed. Round {n + 1} will be scheduled next."
                + (f" Feedback: {feedback}" if feedback else ""),
                "COMPANY",
            )
        await db.commit()
        return await ApplicationRepository.get(db, application.id)
