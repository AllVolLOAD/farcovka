from sqlalchemy import select, func
from app.models.queue import QueueEntry


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

class QueueDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_queue_count(self) -> int:
        result = await self.session.scalar(
            text("SELECT COUNT(*) FROM queue_entries WHERE is_processed = false")
        )
        return result or 0