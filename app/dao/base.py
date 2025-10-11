from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import TypeVar, Generic, Type, Optional
from app.models.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseDAO(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        stmt = select(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> Optional[ModelType]:
        if hasattr(self.model, 'user_id'):
            stmt = select(self.model).where(self.model.user_id == user_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        return None

    async def get_by_chat_id(self, chat_id: int) -> Optional[ModelType]:
        if hasattr(self.model, 'chat_id'):
            stmt = select(self.model).where(self.model.chat_id == chat_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        return None

    async def create(self, **kwargs) -> ModelType:
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def update(self, id: int, **kwargs) -> Optional[ModelType]:
        instance = await self.get_by_id(id)
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            await self.db.commit()
            await self.db.refresh(instance)
        return instance

    async def delete(self, id: int) -> bool:
        instance = await self.get_by_id(id)
        if instance:
            await self.db.delete(instance)
            await self.db.commit()
            return True
        return False