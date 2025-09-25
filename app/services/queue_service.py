from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.models.queue import QueueEntry
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class QueueService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_to_queue(self, user_id: int, username: str = "") -> tuple[bool, int]:
        """
        Добавляет пользователя в очередь
        Возвращает: (успех, текущий размер очереди)
        """
        try:
            # Проверяем, не находится ли пользователь уже в активной очереди
            existing_query = select(QueueEntry).where(
                QueueEntry.user_id == user_id,
                QueueEntry.is_processed == False,
                QueueEntry.created_at >= datetime.utcnow() - timedelta(hours=1)
            )
            existing = await self.session.scalar(existing_query)

            if existing:
                queue_size = await self.get_queue_size()
                return False, queue_size

            # Добавляем в очередь
            new_entry = QueueEntry(user_id=user_id, username=username)
            self.session.add(new_entry)
            await self.session.commit()

            queue_size = await self.get_queue_size()
            logger.info("User %s added to queue. Queue size: %s", user_id, queue_size)

            return True, queue_size

        except Exception as e:
            await self.session.rollback()
            logger.error("Error adding user %s to queue: %s", user_id, e)
            return False, 0

    async def get_queue_size(self) -> int:
        """Возвращает количество пользователей в очереди"""
        query = select(func.count(QueueEntry.id)).where(
            QueueEntry.is_processed == False,
            QueueEntry.created_at >= datetime.utcnow() - timedelta(hours=1)
        )
        result = await self.session.scalar(query)
        return result or 0

    async def get_waiting_users(self) -> list[QueueEntry]:
        """Возвращает список пользователей в очереди"""
        query = select(QueueEntry).where(
            QueueEntry.is_processed == False,
            QueueEntry.created_at >= datetime.utcnow() - timedelta(hours=1)
        ).order_by(QueueEntry.created_at)

        result = await self.session.scalars(query)
        return result.all()

    async def get_queue_users(self) -> List[int]:
        """Возвращает список ID пользователей в очереди"""
        try:
            query = select(QueueEntry.user_id).where(
                QueueEntry.is_processed == False,
                QueueEntry.created_at >= datetime.utcnow() - timedelta(hours=1)
            )
            result = await self.session.scalars(query)
            return list(result)  # Исправлено: используем QueueEntry.user_id
        except Exception as e:
            logger.error("Ошибка получения очереди: %s", e)
            return []

    async def clear_queue(self):
        """Очищает очередь"""
        try:
            # Помечаем все записи как обработанные вместо удаления
            query = select(QueueEntry).where(QueueEntry.is_processed == False)
            entries = await self.session.scalars(query)

            for entry in entries:
                entry.is_processed = True

            await self.session.commit()
            logger.info("Queue cleared successfully")
        except Exception as e:
            await self.session.rollback()
            logger.error("Error clearing queue: %s", e)