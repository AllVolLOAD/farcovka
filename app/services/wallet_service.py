"""Wallet and WalletConnect session management service"""

import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import secrets

from app.models.db.wallet import WalletAccount, WCSession

logger = logging.getLogger(__name__)


class WalletService:
    """Service for managing wallet accounts and WalletConnect sessions"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_wc_session(self, user_id: int) -> dict:
        """
        Create a new WalletConnect session.
        In M1, this is a simplified version - full WC protocol implementation
        would require walletconnect-python library or REST API integration.
        
        Returns session URI and topic.
        """
        try:
            # Generate a unique topic
            topic = f"wc_{secrets.token_urlsafe(32)}"
            
            # Create session record
            session_record = WCSession(
                topic=topic,
                status='pending',
                expiry=datetime.utcnow() + timedelta(minutes=30),
                peer_metadata=None
            )
            
            self.session.add(session_record)
            await self.session.commit()
            await self.session.refresh(session_record)
            
            # Generate WalletConnect URI
            # Note: This is a placeholder. Real WC URI generation requires WC SDK
            uri = f"wc:{topic}@2?relay-protocol=irn&symKey={secrets.token_urlsafe(32)}"
            
            logger.info(f"Created WC session for user {user_id}: {topic}")
            
            return {
                "uri": uri,
                "topic": topic,
                "expiry": session_record.expiry.isoformat() if session_record.expiry else None
            }
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating WC session: {e}", exc_info=True)
            raise
    
    async def register_wallet(
        self,
        user_id: int,
        address: str,
        session_topic: str,
        chain_id: int = 11155111
    ) -> WalletAccount:
        """
        Register a wallet address for user and link to WalletConnect session.
        This is called after user approves connection in their wallet app.
        """
        try:
            # Check if wallet already exists
            stmt = select(WalletAccount).where(WalletAccount.address == address)
            result = await self.session.execute(stmt)
            existing_wallet = result.scalar_one_or_none()
            
            if existing_wallet:
                logger.info(f"Wallet {address} already registered")
                wallet = existing_wallet
            else:
                # Create new wallet account
                wallet = WalletAccount(
                    user_id=user_id,
                    address=address,
                    chain_id=chain_id,
                    wallet_type='external'
                )
                
                self.session.add(wallet)
                await self.session.flush()
                logger.info(f"Registered new wallet {address} for user {user_id}")
            
            # Update WC session
            stmt = select(WCSession).where(WCSession.topic == session_topic)
            result = await self.session.execute(stmt)
            wc_session = result.scalar_one_or_none()
            
            if wc_session:
                wc_session.wallet_id = wallet.id
                wc_session.status = 'active'
                wc_session.peer_metadata = {
                    'address': address,
                    'chain_id': chain_id,
                    'connected_at': datetime.utcnow().isoformat()
                }
            
            await self.session.commit()
            await self.session.refresh(wallet)
            
            return wallet
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error registering wallet: {e}", exc_info=True)
            raise
    
    async def get_user_wallets(self, user_id: int) -> list[WalletAccount]:
        """Get all wallets for a user"""
        stmt = select(WalletAccount).where(WalletAccount.user_id == user_id)
        result = await self.session.execute(stmt)
        wallets = result.scalars().all()
        return list(wallets)
    
    async def get_wallet_by_address(self, address: str) -> WalletAccount | None:
        """Get wallet by address"""
        stmt = select(WalletAccount).where(WalletAccount.address == address)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_session(self, topic: str) -> WCSession | None:
        """Get WalletConnect session by topic"""
        stmt = select(WCSession).where(WCSession.topic == topic)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def disconnect_session(self, topic: str):
        """Disconnect WalletConnect session"""
        try:
            stmt = select(WCSession).where(WCSession.topic == topic)
            result = await self.session.execute(stmt)
            session = result.scalar_one_or_none()
            
            if session:
                session.status = 'disconnected'
                await self.session.commit()
                logger.info(f"Disconnected WC session: {topic}")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error disconnecting session: {e}", exc_info=True)
            raise
    
    async def cleanup_expired_sessions(self):
        """Clean up expired WalletConnect sessions (background task)"""
        try:
            stmt = select(WCSession).where(
                WCSession.status == 'active',
                WCSession.expiry < datetime.utcnow()
            )
            result = await self.session.execute(stmt)
            expired_sessions = result.scalars().all()
            
            for session in expired_sessions:
                session.status = 'expired'
                logger.info(f"Expired WC session: {session.topic}")
            
            if expired_sessions:
                await self.session.commit()
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error cleaning up sessions: {e}", exc_info=True)

