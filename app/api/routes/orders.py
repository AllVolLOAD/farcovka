"""Order management routes"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user, require_admin
from app.models import dto
from app.models.db.balance import UserBalance
from app.models.db.hot_wallet import HotWallet
from app.models.db.user import User
from app.services.hot_balance_service import HOTBalanceService
from app.services.order_service import OrderService


router = APIRouter()


class CreateOrderRequest(BaseModel):
    """Request to create a new order"""
    wallet_id: int | None = None
    wallet_mode: str = "COLD"  # "COLD" or "HOT"
    type: str  # "buy" or "sell"
    currency_pair: str  # e.g., "USD/RUB"
    amount_crypto: Decimal
    amount_fiat: Decimal
    rate: Decimal


class OrderResponse(BaseModel):
    """Order response"""
    id: int
    user_id: int
    wallet_id: int | None
    type: str
    wallet_mode: str
    currency_pair: str
    amount_crypto: str
    amount_fiat: str
    rate: str
    status: str
    deposit_address: str | None
    created_at: str | None
    updated_at: str | None


class HotBalanceResponse(BaseModel):
    token: str
    balance: str


class HotDepositResponse(BaseModel):
    vault_address: str
    chain_id: int
    note: str | None = None


class HotWithdrawRequest(BaseModel):
    amount_crypto: Decimal
    to_address: str
    token: str = "USDT"


class HotWithdrawResponse(BaseModel):
    status: str
    token: str
    amount: str
    message: str


@router.post("/", response_model=OrderResponse)
async def create_order(
    data: CreateOrderRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dto.User = Depends(get_current_user)
):
    order_service = OrderService(session)
    order = await order_service.create_order(
        user_id=current_user.tg_id,
        wallet_id=data.wallet_id,
        order_type=data.type,
        currency_pair=data.currency_pair,
        amount_crypto=data.amount_crypto,
        amount_fiat=data.amount_fiat,
        rate=data.rate,
        wallet_mode=data.wallet_mode,
    )
    
    return OrderResponse(**order.to_dict())


@router.get("/my", response_model=list[OrderResponse])
async def list_my_orders(
    session: AsyncSession = Depends(get_db),
    current_user: dto.User = Depends(get_current_user)
):
    order_service = OrderService(session)
    orders = await order_service.get_user_orders(current_user.tg_id)
    return [OrderResponse(**order.to_dict()) for order in orders]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dto.User = Depends(get_current_user)
):
    order_service = OrderService(session)
    order = await order_service.get_order(order_id)

    if not order or order.user_id != current_user.tg_id:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderResponse(**order.to_dict())


@router.post("/{order_id}/process")
async def process_order_admin(
    order_id: int,
    session: AsyncSession = Depends(get_db),
    admin: dto.User = Depends(require_admin)
):
    """
    Manually trigger order processing (admin only).
    Used in M1 for manual withdrawal approval.
    """
    # TODO: Implement OrderService.process_withdrawal
    raise HTTPException(status_code=501, detail="Order processing not yet implemented")


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dto.User = Depends(get_current_user)
):
    order_service = OrderService(session)
    await order_service.cancel_order(order_id, current_user.tg_id)
    return {"status": "cancelled", "order_id": order_id}


@router.get("/hot/balance", response_model=list[HotBalanceResponse])
async def get_hot_balance(
    token: str | None = Query(default=None, description="Filter by token symbol, e.g., USDT"),
    session: AsyncSession = Depends(get_db),
    current_user: dto.User = Depends(get_current_user)
):
    await _ensure_hot_access(session, current_user.tg_id)

    if token:
        balance_service = HOTBalanceService(session)
        balance = await balance_service.get_balance(current_user.tg_id, token)
        return [HotBalanceResponse(token=token, balance=str(balance))]

    stmt = select(UserBalance).where(UserBalance.user_id == current_user.tg_id)
    result = await session.execute(stmt)
    balances = result.scalars().all()

    return [
        HotBalanceResponse(token=row.token, balance=str(row.balance))
        for row in balances
    ]


@router.post("/hot/deposit/request", response_model=HotDepositResponse)
async def request_hot_deposit(
    session: AsyncSession = Depends(get_db),
    current_user: dto.User = Depends(get_current_user)
):
    await _ensure_hot_access(session, current_user.tg_id)

    stmt = (
        select(HotWallet)
        .where(HotWallet.name == 'vault', HotWallet.is_active.is_(True))
        .order_by(HotWallet.id.asc())
        .limit(1)
    )
    result = await session.execute(stmt)
    vault = result.scalar_one_or_none()

    if not vault:
        raise HTTPException(status_code=503, detail="Vault address is not configured yet")

    return HotDepositResponse(
        vault_address=vault.address,
        chain_id=vault.chain_id,
        note="Send USDT on Sepolia testnet. Confirmation handled automatically later.",
    )


@router.post("/hot/withdraw", response_model=HotWithdrawResponse)
async def request_hot_withdraw(
    data: HotWithdrawRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dto.User = Depends(get_current_user)
):
    await _ensure_hot_access(session, current_user.tg_id)

    balance_service = HOTBalanceService(session)
    has_balance = await balance_service.check_sufficient_balance(
        current_user.tg_id,
        data.amount_crypto,
        data.token,
    )

    if not has_balance:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    await balance_service.update_balance(
        current_user.tg_id,
        data.token,
        Decimal(0) - Decimal(data.amount_crypto),
        reason="withdraw_request",
    )

    message = (
        "Withdrawal requested. Funds will be sent from the vault once the admin approves."
    )
    return HotWithdrawResponse(
        status="pending",
        token=data.token,
        amount=str(data.amount_crypto),
        message=message,
    )


async def _ensure_hot_access(session: AsyncSession, user_id: int) -> User:
    stmt = select(User).where(User.tg_id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not getattr(user, "hot_access_enabled", False):
        raise HTTPException(status_code=403, detail="HOT mode access is not enabled")
    return user

