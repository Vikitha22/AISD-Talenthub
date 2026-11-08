from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import ProfileAudit, AcademicUpdateRequest
from app.repositories.repository import StudentRepository
from app.core.timeutil import utcnow

class ProfileService:
    @staticmethod
    async def update(db: AsyncSession, student_id: int, data: dict):
        student = await StudentRepository.get(db, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student profile not found")
        for field in ("phone", "skills"):
            if field in data and data[field] is not None:
                old = getattr(student, field) or ""
                new = data[field]
                if old != new:
                    StudentRepository.add_audit(db, ProfileAudit(student_id=student_id, field=field, old_value=str(old), new_value=str(new)))
                    setattr(student, field, new)
        await db.commit()
        return student

    @staticmethod
    async def request_academic_update(db: AsyncSession, student_id: int, field: str, value):
        student = await StudentRepository.get(db, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student profile not found")
        old = getattr(student, field)
        if old == value:
            raise HTTPException(status_code=400, detail="The requested value is the same as your current value")
        pending = (await db.execute(select(AcademicUpdateRequest).where(AcademicUpdateRequest.student_id == student_id, AcademicUpdateRequest.field == field, AcademicUpdateRequest.status == "PENDING"))).scalar_one_or_none()
        if pending:
            raise HTTPException(status_code=409, detail="You already have a pending request for this field")
        req = AcademicUpdateRequest(student_id=student_id, field=field, old_value=str(old), requested_value=str(value))
        db.add(req); await db.commit(); await db.refresh(req)
        return req

    @staticmethod
    async def list_requests(db: AsyncSession):
        rows = (await db.execute(select(AcademicUpdateRequest).order_by(AcademicUpdateRequest.created_at.desc()))).scalars().all()
        return [{"id": r.id, "student_id": r.student_id, "student_name": (await StudentRepository.get(db, r.student_id)).name, "field": r.field, "old_value": r.old_value, "requested_value": r.requested_value, "status": r.status, "note": r.coordinator_note, "created_at": r.created_at.isoformat()} for r in rows]

    @staticmethod
    async def review_request(db: AsyncSession, request_id: int, decision: str, note: str):
        req = await db.get(AcademicUpdateRequest, request_id)
        if not req: raise HTTPException(status_code=404, detail="Academic update request not found")
        if req.status != "PENDING": raise HTTPException(status_code=400, detail="This request has already been reviewed")
        if decision == "REJECT" and len(note.strip()) < 5: raise HTTPException(status_code=400, detail="A rejection reason of at least 5 characters is required")
        student = await StudentRepository.get(db, req.student_id)
        if decision == "APPROVE":
            value = float(req.requested_value) if req.field == "cgpa" else int(req.requested_value)
            setattr(student, req.field, value)
            StudentRepository.add_audit(db, ProfileAudit(student_id=req.student_id, field=req.field, old_value=req.old_value, new_value=str(value)))
            req.status = "APPROVED"
        else: req.status = "REJECTED"
        req.coordinator_note = note.strip(); req.reviewed_at = utcnow()
        await db.commit(); return {"id": req.id, "status": req.status, "note": req.coordinator_note}
