
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import dto


class UserDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_users_count(self) -> int:
        # Используем прямое SQL с существующей таблицей
        result = await self.session.scalar(text("SELECT COUNT(*) FROM user_from_tg"))
        return result or 0

    async def upsert_user(self, user: dto.User) -> dto.User:
        # Временно закомментируем этот метод или используем заглушку
        return user  # Заглушка

        # Или если нужна реальная реализация, используем прямое SQL:
        # from sqlalchemy import text
        # await self.session.execute(text("INSERT OR UPDATE ..."))
        # return user