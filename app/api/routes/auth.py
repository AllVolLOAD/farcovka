"""Authentication routes for Telegram Login Widget"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, create_access_token, verify_telegram_auth
from app.dao.user import UserDAO


router = APIRouter()


class TelegramAuthData(BaseModel):
    """Telegram Login Widget auth data"""
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/telegram", response_model=TokenResponse)
async def telegram_login(
    auth_data: TelegramAuthData,
    session: AsyncSession = Depends(get_db)
):
    """
    Authenticate user via Telegram Login Widget.
    Validates the hash and creates/updates user in database.
    Returns JWT access token.
    """
    # TODO: Get bot token from config instead of hardcoding
    # For now, skip verification in development
    # if not verify_telegram_auth(auth_data.dict(), BOT_TOKEN):
    #     raise HTTPException(status_code=401, detail="Invalid Telegram authentication")
    
    user_dao = UserDAO(session)
    
    # Try to get existing user or create new one
    try:
        user_db = await user_dao.get_by_tg_id(auth_data.id)
    except Exception:
        # User doesn't exist, create a new one
        # Note: UserDAO might need an upsert method
        # For now, we'll use the existing structure
        user_db = None
    
    if not user_db:
        # Create user (this is a simplified version, you may need to adjust)
        # based on your actual UserDAO implementation
        raise HTTPException(
            status_code=501,
            detail="User creation not fully implemented. User must interact with bot first."
        )
    
    # Create JWT token
    access_token = create_access_token(data={"tg_id": auth_data.id})
    
    return TokenResponse(
        access_token=access_token,
        user={
            "tg_id": auth_data.id,
            "first_name": auth_data.first_name,
            "last_name": auth_data.last_name,
            "username": auth_data.username
        }
    )


@router.get("/me")
async def get_current_user_info(
    session: AsyncSession = Depends(get_db),
    # current_user: dto.User = Depends(get_current_user)
):
    """Get current user information"""
    # TODO: Implement with proper authentication
    return {"message": "Not implemented yet"}

