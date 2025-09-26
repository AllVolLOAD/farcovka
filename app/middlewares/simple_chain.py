from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from app.models.config.main import BotConfig

class SimpleConfigMiddleware(BaseMiddleware):
    """Только конфиг"""
    def __init__(self, config: BotConfig):
        self.config = config

    async def __call__(self, handler, event, data):
        data["config"] = self.config
        return await handler(event, data)

class SimpleDbMiddleware(BaseMiddleware):
    """Только сессия БД"""
    def __init__(self, pool: async_sessionmaker[AsyncSession]):
        self.pool = pool

    async def __call__(self, handler, event, data):
        async with self.pool() as session:
            data["session"] = session
            return await handler(event, data)
