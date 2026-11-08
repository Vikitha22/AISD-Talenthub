"""Turns ORM objects into JSON-ready dicts. Also computes the plain-language "what happens next" text."""
from app.core import constants as C
from app.core.timeutil import fmt, iso, utcnow
from app.models.models import Application, Interview, JobListing, Offer, Policy, Student
from app.services.eligibility_service import split_branches
import json


def serialize_student(s: Student) -> dict:
    return {
        "id": s.id,
        "roll_number": s.roll_number,
        "name": s.name,
        "email": s.email,
        "phone": s.phone or "",
        "branch": s.branch,
        "cgpa": s.cgpa,
        "active_backlogs": s.active_backlogs,
        "skills": s.skills or "",
    }


def serialize_job(job: JobListing, *, include_counts: bool = False, student_ctx: dict | None = None) -> dict:
    data = {
        "id": job.id,
        "company_id": job.company_id,
        "company_name": job.company.name if job.company else None,
        "role_title": job.role_title,
        "description": job.description,
        "job_type": job.job_type,
        "location": job.location,
        "package_lpa": job.package_lpa,
        "min_cgpa": job.min_cgpa,
        "max_backlogs": job.max_backlogs,
        "allowed_branches": split_branches(job.allowed_branches),
        "all_branches": job.allowed_branches == "*",
        "skills_required": job.skills_required or "",
        "selection_process": job.selection_process or "",
        "selection_rounds": json.loads(job.selection_rounds or "[]"),
        "num_rounds": job.num_rounds,
        "deadline": iso(job.deadline),
        "created_at": iso(job.created_at),
        "is_open": job.deadline > utcnow(),
    }
    if include_counts:
        data["applicants"] = len(job.applications)
    if student_ctx is not None:
        data.update(student_ctx)
    return data


def serialize_interview(i: Interview) -> dict:
    from datetime import timedelta

    return {
        "id": i.id,
        "round_number": i.round_number,
        "round_type": i.round_type,
        "mode": i.mode,
        "location": i.location,
        "scheduled_at": iso(i.scheduled_at),
        "ends_at": iso(i.scheduled_at + timedelta(minutes=i.duration_minutes)),
        "duration_minutes": i.duration_minutes,
        "result": i.result,
        "feedback": i.feedback or "",
        "notes": i.notes or "",
    }


def serialize_offer(o: Offer | None) -> dict | None:
    if not o:
        return None
    return {
        "reference": o.reference,
        "package_lpa": o.package_lpa,
        "status": o.status,
        "issued_at": iso(o.issued_at),
        "respond_by": iso(o.respond_by),
        "responded_at": iso(o.responded_at),
        "response_note": o.response_note or "",
    }


def serialize_policy(p: Policy | None, full: bool = True) -> dict | None:
    if not p:
        return None
    d = {"id": p.id, "version": p.version, "title": p.title, "is_active": p.is_active, "published_at": iso(p.published_at)}
    if full:
        d["content"] = p.content
    return d


def next_step(a: Application, viewer: str) -> str:
    company = a.job.company.name if a.job and a.job.company else "the company"
    student_view = viewer == "STUDENT"
    s = a.status

    if s == C.APPLIED:
        return (f"Your application is with {company}. They will shortlist or reject it and the decision will appear here."
                if student_view else "Action needed: shortlist or reject this applicant.")
    if s == C.SHORTLISTED:
        return (f"You are shortlisted. {company} will conduct its published selection process and update the decision here."
                if student_view else "Action needed: complete the selection process outside TalentHub, then record the final decision.")
    if s == C.INTERVIEW_SCHEDULED:
        return "Contact the company for details about the selection process in progress."
    if s == C.INTERVIEW_CLEARED:
        return (f"The selection process is complete. Waiting for {company} to issue an offer."
                if student_view else "Action needed: issue an offer.")
    if s == C.OFFERED and a.offer:
        return (f"Offer pending your response: accept or decline before {fmt(a.offer.respond_by)}."
                if student_view else f"Waiting for the student to respond before {fmt(a.offer.respond_by)}.")
    if s == C.ACCEPTED:
        return "Offer accepted - placement confirmed." if student_view else "The student accepted the offer. Placement confirmed."
    if s == C.DECLINED:
        return "This offer was declined."
    if s == C.OFFER_EXPIRED:
        return "The offer expired because it was not answered in time."
    if s == C.REJECTED:
        return f"Not selected. Reason: {a.rejection_reason or 'not recorded'}"
    if s == C.WITHDRAWN:
        return "This application was withdrawn."
    return "Check the application history for the latest update."


def serialize_application(a: Application, viewer: str) -> dict:
    return {
        "id": a.id,
        "status": a.status,
        "applied_at": iso(a.applied_at),
        "status_updated_at": iso(a.status_updated_at),
        "rejection_reason": a.rejection_reason,
        "next_step": next_step(a, viewer),
        "student": serialize_student(a.student),
        "job": serialize_job(a.job),
        "company_name": a.job.company.name if a.job.company else None,
        "interviews": [serialize_interview(i) for i in sorted(a.interviews, key=lambda i: i.round_number)],
        "offer": serialize_offer(a.offer),
        "events": [
            {"status": e.status, "note": e.note, "actor_role": e.actor_role, "created_at": iso(e.created_at)}
            for e in a.events
        ],
    }
