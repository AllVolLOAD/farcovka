# dao/user.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.db.user import User
from app.models.dto.user import UserCreate, UserInDB
from app.dao.base import BaseDAO

class UserDAO(BaseDAO[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_user_id(self, user_id: int) -> UserInDB | None:
        user = await super().get_by_user_id(user_id)
        return UserInDB.model_validate(user) if user else None

    async def upsert_user(self, user_data: UserCreate) -> UserInDB:
        """Создает или обновляет пользователя"""
        existing_user = await self.get_by_user_id(user_data.user_id)

        if existing_user:
            user = await super().get_by_user_id(user_data.user_id)
            for key, value in user_data.model_dump().items():
                setattr(user, key, value)
        else:
            user = User(**user_data.model_dump())
            self.db.add(user)

        await self.db.commit()
        await self.db.refresh(user)
        return UserInDB.model_validate(user)