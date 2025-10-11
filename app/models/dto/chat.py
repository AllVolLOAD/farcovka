from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Старые классы для совместимости
class Chat(BaseModel):
    id: int
    chat_id: int
    type: str
    title: Optional[str] = None
    username: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Новые классы
class ChatBase(BaseModel):
    chat_id: int
    type: str
    title: Optional[str] = None
    username: Optional[str] = None
    is_active: bool = True

class ChatCreate(ChatBase):
    pass

class ChatUpdate(BaseModel):
    title: Optional[str] = None
    username: Optional[str] = None
    is_active: Optional[bool] = None

class ChatInDB(ChatBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True