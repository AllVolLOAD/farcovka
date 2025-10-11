from sqlalchemy.ext.asyncio import AsyncSession
from app.dao.user import UserDAO
from app.dao.chat import ChatDAO
from app.dao.queue import QueueDAO
from app.dao.parsed_rate import ParsedRateDAO

class HolderDao:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user = UserDAO(session)
        self.chat = ChatDAO(session)
        self.queue = QueueDAO(session)
        self.parsed_rate = ParsedRateDAO(session)

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()