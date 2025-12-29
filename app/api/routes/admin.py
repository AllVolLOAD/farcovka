from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_admin
from app.models.db.hot_wallet import HotWallet
from app.models.db.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])


class HotAccessUpdateRequest(BaseModel):
    enabled: bool


class HotAccessResponse(BaseModel):
    user_id: int
    hot_access_enabled: bool


class HotWalletResponse(BaseModel):
    id: int
    name: str
    address: str
    chain_id: int
    is_active: bool
    created_at: str | None = None


@router.post("/users/{user_id}/hot-access", response_model=HotAccessResponse)
async def set_hot_access(
    user_id: int,
    data: HotAccessUpdateRequest,
    session: AsyncSession = Depends(get_db),
    admin=Depends(require_admin)
):
    stmt = select(User).where(User.tg_id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hot_access_enabled = data.enabled
    await session.commit()

    return HotAccessResponse(user_id=user.tg_id, hot_access_enabled=user.hot_access_enabled)


@router.get("/hot-wallets", response_model=list[HotWalletResponse])
async def list_hot_wallets(
    session: AsyncSession = Depends(get_db),
    admin=Depends(require_admin)
):
    result = await session.execute(select(HotWallet))
    wallets = result.scalars().all()

    return [
        HotWalletResponse(
            id=wallet.id,
            name=wallet.name,
            address=wallet.address,
            chain_id=wallet.chain_id,
            is_active=wallet.is_active,
            created_at=wallet.created_at.isoformat() if wallet.created_at else None,
        )
        for wallet in wallets
    ]

