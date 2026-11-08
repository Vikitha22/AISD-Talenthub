from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, require_role
from app.schemas.schemas import OfferCreate, OfferRespondRequest
from app.services.application_service import get_owned_application
from app.services.offer_service import OfferService
from app.services.serializers import serialize_application

router = APIRouter(prefix="/offers", tags=["offers"])


@router.post("")
async def issue_offer(body: OfferCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(require_role("COMPANY"))):
    application = await get_owned_application(db, user.linked_id, body.application_id)
    app = await OfferService.issue(db, application, body.package_lpa, body.respond_within_days)
    return serialize_application(app, "COMPANY")


@router.patch("/{application_id}/respond")
async def respond_to_offer(
    application_id: int, body: OfferRespondRequest, db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("STUDENT")),
):
    app = await OfferService.respond(db, user.linked_id, application_id, body.accept, body.note)
    return serialize_application(app, "STUDENT")
