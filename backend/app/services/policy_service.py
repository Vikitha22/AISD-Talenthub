from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timeutil import utcnow
from app.models.models import Policy, PolicyAcceptance
from app.repositories.repository import PolicyRepository


class PolicyService:
    @staticmethod
    async def publish(db: AsyncSession, title: str, content: str) -> Policy:
        """Publishing creates a NEW version and retires the old one; students must accept it before their next job application."""
        for old in await PolicyRepository.list_all(db):
            old.is_active = False
        policy = Policy(
            version=await PolicyRepository.max_version(db) + 1,
            title=title.strip(),
            content=content.strip(),
            is_active=True,
        )
        PolicyRepository.add(db, policy)
        await db.commit()
        return policy

    @staticmethod
    async def status_for_student(db: AsyncSession, student_id: int) -> dict:
        policy = await PolicyRepository.get_active(db)
        if not policy:
            return {"policy": None, "accepted": True, "accepted_at": None}
        acc = await PolicyRepository.get_acceptance(db, student_id, policy.id)
        return {"policy": policy, "accepted": acc is not None, "accepted_at": acc.accepted_at if acc else None}

    @staticmethod
    async def accept(db: AsyncSession, student_id: int, policy_id: int, agree: bool) -> dict:
        if not agree:
            raise HTTPException(status_code=400, detail="You must tick the checkbox to accept the Placement Policy.")
        policy = await PolicyRepository.get_active(db)
        if not policy or policy.id != policy_id:
            raise HTTPException(status_code=400, detail="That policy version is no longer active. Please reload and read the latest one.")
        if not await PolicyRepository.get_acceptance(db, student_id, policy_id):
            PolicyRepository.add(db, PolicyAcceptance(student_id=student_id, policy_id=policy_id, accepted_at=utcnow()))
            await db.commit()
        return await PolicyService.status_for_student(db, student_id)

    @staticmethod
    async def list_all(db: AsyncSession) -> list[dict]:
        out = []
        for p in await PolicyRepository.list_all(db):
            out.append({"policy": p, "acceptances": await PolicyRepository.count_acceptances(db, p.id)})
        return out
