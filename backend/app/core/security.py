from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, get_secret_key
from app.core.database import get_db
from app.models.models import User

SECRET_KEY = get_secret_key()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def _prep(password: str) -> bytes:
    return password.encode("utf-8")[:72]  # bcrypt only uses the first 72 bytes


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prep(password), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_prep(plain_password), hashed_password.encode())
    except ValueError:
        return False


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@dataclass
class CurrentUser:
    id: int
    role: str
    linked_id: int | None
    name: str


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> CurrentUser:
    error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise error
    user = await db.get(User, user_id)  # token is only valid while the account still exists
    if not user:
        raise error
    linked = user.student_id if user.role == "STUDENT" else user.company_id if user.role == "COMPANY" else None
    return CurrentUser(id=user.id, role=user.role, linked_id=linked, name=user.display_name)


def require_role(*roles: str):
    async def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You are not authorised for this action")
        return user

    return checker
