from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_role
from app.repositories.repository import CompanyRepository

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("")
async def list_companies(db: AsyncSession = Depends(get_db), _=Depends(require_role("COORDINATOR", "STUDENT"))):
    return [{"id": c.id, "name": c.name, "description": c.description} for c in await CompanyRepository.list_all(db)]
