"""WalletConnect session management routes"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.models import dto


router = APIRouter()


class WCSessionRequest(BaseModel):
    """Request to create WalletConnect session"""
    pass  # No parameters needed for session creation


class WCSessionResponse(BaseModel):
    """WalletConnect session response"""
    uri: str
    topic: str


class ApproveSessionRequest(BaseModel):
    """Request to approve WalletConnect session"""
    address: str
    chain_id: int = 11155111  # Sepolia by default


class WalletResponse(BaseModel):
    """Wallet account response"""
    id: int
    address: str
    chain_id: int
    wallet_type: str
    created_at: str | None


@router.post("/sessions", response_model=WCSessionResponse)
async def create_wc_session(
    session: AsyncSession = Depends(get_db),
    current_user: dto.User = Depends(get_current_user)
):
    """
    Create a new WalletConnect session.
    Returns a URI that can be used to connect external wallet (MetaMask, Trust Wallet, etc.)
    """
    # TODO: Implement WalletService.create_wc_session
    # For now, return a placeholder
    raise HTTPException(status_code=501, detail="WalletConnect session creation not yet implemented")


@router.post("/sessions/{topic}/approve")
async def approve_session(
    topic: str,
    data: ApproveSessionRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dto.User = Depends(get_current_user)
):
    """
    Approve WalletConnect session and register wallet address.
    Called after user approves connection in their wallet app.
    """
    # TODO: Implement WalletService.register_wallet
    raise HTTPException(status_code=501, detail="Session approval not yet implemented")


@router.get("/sessions/{topic}")
async def get_session(
    topic: str,
    session: AsyncSession = Depends(get_db),
    current_user: dto.User = Depends(get_current_user)
):
    """
    Get WalletConnect session details by topic.
    """
    # TODO: Implement WalletService.get_session
    raise HTTPException(status_code=501, detail="Session retrieval not yet implemented")


@router.delete("/sessions/{topic}")
async def disconnect_session(
    topic: str,
    session: AsyncSession = Depends(get_db),
    current_user: dto.User = Depends(get_current_user)
):
    """
    Disconnect WalletConnect session.
    """
    # TODO: Implement WalletService.disconnect_session
    raise HTTPException(status_code=501, detail="Session disconnect not yet implemented")


@router.get("/wallets", response_model=list[WalletResponse])
async def list_wallets(
    session: AsyncSession = Depends(get_db),
    current_user: dto.User = Depends(get_current_user)
):
    """
    List all wallets connected to current user.
    """
    # TODO: Implement WalletService.get_user_wallets
    return []

