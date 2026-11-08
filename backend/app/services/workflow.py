"""Shared helpers so every status change leaves an audit event ("no silent decisions")."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timeutil import utcnow
from app.models.models import Application, ApplicationEvent
from app.repositories.repository import ApplicationRepository


def set_status(db: AsyncSession, application: Application, status: str, note: str, actor_role: str) -> None:
    application.status = status
    application.status_updated_at = utcnow()
    ApplicationRepository.add_event(
        db, ApplicationEvent(application_id=application.id, status=status, note=note, actor_role=actor_role)
    )


def add_note(db: AsyncSession, application: Application, note: str, actor_role: str) -> None:
    """Record something that happened without changing the status (e.g. 'Round 1 passed')."""
    ApplicationRepository.add_event(
        db, ApplicationEvent(application_id=application.id, status=application.status, note=note, actor_role=actor_role)
    )
