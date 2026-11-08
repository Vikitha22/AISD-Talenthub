from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.repositories.repository import UserRepository


class AuthService:
    @staticmethod
    async def login(db: AsyncSession, email: str, password: str) -> dict:
        user = await UserRepository.get_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        linked_id = user.student_id if user.role == "STUDENT" else user.company_id if user.role == "COMPANY" else None
        token = create_access_token({"sub": str(user.id), "role": user.role})
        return {
            "access_token": token,
            "token_type": "bearer",
            "role": user.role,
            "user_id": user.id,
            "name": user.display_name,
            "linked_id": linked_id,
        }
