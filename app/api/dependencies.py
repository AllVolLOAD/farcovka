"""FastAPI dependencies for database session, authentication, etc."""

from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from datetime import datetime, timedelta
import hashlib
import hmac

from app.models.db import create_pool
from app.dao.user import UserDAO
from app.models import dto


# JWT Configuration
SECRET_KEY = "your-secret-key-change-in-production"  # TODO: Move to config
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

security = HTTPBearer()

# Global pool (will be set in main.py)
_pool = None


def set_pool(pool):
    """Set the global database pool"""
    global _pool
    _pool = pool


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    if _pool is None:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    async with _pool() as session:
        yield session


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_telegram_auth(auth_data: dict, bot_token: str) -> bool:
    """Verify Telegram Login Widget data"""
    check_hash = auth_data.get('hash')
    if not check_hash:
        return False
    
    data_check_arr = []
    for key, value in sorted(auth_data.items()):
        if key != 'hash':
            data_check_arr.append(f'{key}={value}')
    
    data_check_string = '\n'.join(data_check_arr)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    hash_value = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    return hash_value == check_hash


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db)
) -> dto.User:
    """Dependency to get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        tg_id: int = payload.get("tg_id")
        if tg_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user_dao = UserDAO(session)
    user = await user_dao.get_by_tg_id(tg_id)
    if user is None:
        raise credentials_exception
    
    return user.to_dto()


async def require_admin(
    current_user: dto.User = Depends(get_current_user)
) -> dto.User:
    """Dependency to require admin privileges"""
    # TODO: Implement actual admin check (e.g., check against config.superusers)
    # For now, just return the user
    return current_user

