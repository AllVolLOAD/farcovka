from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from app.dao.user import UserDAO
from app.dao.chat import ChatDAO
from app.dao.queue import QueueDAO

@dataclass
class HolderDao:  # ← Исправляем на HolderDao (с маленькой 'o')
    session: AsyncSession
    user: UserDAO = field(init=False)
    chat: ChatDAO = field(init=False)
    queue: QueueDAO = field(init=False)

    def __post_init__(self):
        self.user = UserDAO(self.session)
        self.chat = ChatDAO(self.session)
        self.queue = QueueDAO(self.session)


# Удаляем лишний класс HolderDao если он есть
