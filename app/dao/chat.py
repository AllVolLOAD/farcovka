from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.db.chat import Chat
from app.models.dto.chat import ChatCreate, ChatInDB
from app.dao.base import BaseDAO


class ChatDAO(BaseDAO[Chat]):
    def __init__(self, db: AsyncSession):
        super().__init__(Chat, db)

    async def get_by_chat_id(self, chat_id: int) -> ChatInDB | None:
        chat = await super().get_by_chat_id(chat_id)
        if chat:
            return ChatInDB(
                id=chat.id,
                chat_id=chat.chat_id,
                type=chat.type,
                title=chat.title,
                username=chat.username,
                is_active=chat.is_active,
                created_at=chat.created_at,
                updated_at=chat.updated_at
            )
        return None

    async def upsert_chat(self, chat_data: ChatCreate) -> ChatInDB:
        """Создает или обновляет чат"""
        existing_chat = await self.get_by_chat_id(chat_data.chat_id)

        if existing_chat:
            chat = await super().get_by_chat_id(chat_data.chat_id)
            chat.type = chat_data.type
            chat.title = chat_data.title
            chat.username = chat_data.username
            chat.is_active = chat_data.is_active
        else:
            chat = Chat(**chat_data.model_dump())
            self.db.add(chat)

        await self.db.commit()
        await self.db.refresh(chat)

        return ChatInDB(
            id=chat.id,
            chat_id=chat.chat_id,
            type=chat.type,
            title=chat.title,
            username=chat.username,
            is_active=chat.is_active,
            created_at=chat.created_at,
            updated_at=chat.updated_at
        )