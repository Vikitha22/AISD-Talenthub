from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import constants as C
from app.core.timeutil import fmt, utcnow
from app.models.models import Offer
from app.repositories.repository import PolicyRepository
from app.repositories.repository import ApplicationRepository, OfferRepository
from app.services.workflow import set_status


def _bad(msg: str) -> HTTPException:
    return HTTPException(status_code=400, detail={"message": msg, "reasons": [], "code": None})


class OfferService:
    @staticmethod
    async def expire_overdue(db: AsyncSession) -> None:
        """Offers the student never answered in time become EXPIRED (recorded, not silent)."""
        overdue = await OfferRepository.list_overdue(db, utcnow())
        if not overdue:
            return
        for offer in overdue:
            application = await ApplicationRepository.get(db, offer.application_id)
            offer.status = C.OFFER_EXPIRED_STATE
            offer.responded_at = None
            if application and application.status == C.OFFERED:
                set_status(
                    db,
                    application,
                    C.OFFER_EXPIRED,
                    f"The offer expired because no response was received by {fmt(offer.respond_by)}.",
                    "SYSTEM",
                )
        await db.commit()

    @staticmethod
    async def issue(db: AsyncSession, application, package_lpa: float | None, respond_within_days: int):
        """`application` has already been ownership-checked by the caller."""
        if application.status != C.INTERVIEW_CLEARED:
            raise _bad(
                "An offer can only be issued after the company marks the selection process as completed "
                f"(this application is {application.status})."
            )
        if await OfferRepository.get_by_application(db, application.id):
            raise _bad("An offer has already been issued for this application.")

        package = package_lpa if package_lpa is not None else application.job.package_lpa
        now = utcnow()
        offer = Offer(
            application_id=application.id,
            package_lpa=package,
            status=C.OFFER_PENDING,
            issued_at=now,
            respond_by=now + timedelta(days=respond_within_days),
        )
        OfferRepository.add(db, offer)
        await db.flush()
        offer.reference = f"OFR-{now.year}-{offer.id:05d}"
        set_status(
            db,
            application,
            C.OFFERED,
            f"Offer {offer.reference} issued: {package:g} LPA. The student must respond by {fmt(offer.respond_by)}.",
            "COMPANY",
        )
        await db.commit()
        return await ApplicationRepository.get(db, application.id)

    @staticmethod
    async def respond(db: AsyncSession, student_id: int, application_id: int, accept: bool, note: str):
        await OfferService.expire_overdue(db)
        application = await ApplicationRepository.get(db, application_id)
        if not application or application.student_id != student_id:
            raise HTTPException(status_code=404, detail="Application not found")
        offer = application.offer
        if not offer:
            raise HTTPException(status_code=404, detail="No offer exists for this application")
        if offer.status == C.OFFER_EXPIRED_STATE:
            raise _bad(f"This offer expired on {fmt(offer.respond_by)} and can no longer be answered.")
        if offer.status != C.OFFER_PENDING:
            raise _bad(f"You have already responded to this offer ({offer.status}). The decision is final.")

        now = utcnow()
        offer.responded_at = now
        offer.response_note = (note or "").strip()

        if not accept:
            offer.status = C.OFFER_DECLINED
            set_status(
                db, application, C.DECLINED,
                "The student declined the offer." + (f" Note: {offer.response_note}" if offer.response_note else ""),
                "STUDENT",
            )
            await db.commit()
            return await ApplicationRepository.get(db, application_id)

        if await ApplicationRepository.student_has_status(db, student_id, C.ACCEPTED):
            raise _bad("You have already accepted another offer. The policy allows only one accepted offer.")

        offer.status = C.OFFER_ACCEPTED
        set_status(
            db, application, C.ACCEPTED,
            "The student accepted the offer." + (f" Note: {offer.response_note}" if offer.response_note else ""),
            "STUDENT",
        )
        # One-offer policy: close everything else this student still has open, and record why.
        for other in await ApplicationRepository.list_other_by_student(db, student_id, application_id):
            if other.status == C.OFFERED and other.offer and other.offer.status == C.OFFER_PENDING:
                other.offer.status = C.OFFER_DECLINED
                other.offer.responded_at = now
                other.offer.response_note = "Closed automatically: the student accepted another offer."
                set_status(db, other, C.DECLINED, "Offer closed automatically because the student accepted another offer.", "SYSTEM")
            elif other.status in C.OPEN_STATUSES:
                set_status(db, other, C.WITHDRAWN, "Application withdrawn automatically because the student accepted another offer.", "SYSTEM")
        await db.commit()
        return await ApplicationRepository.get(db, application_id)
