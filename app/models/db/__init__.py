from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config.main import load_config
from app.models.config.main import Paths
import os
from pathlib import Path

def get_paths() -> Paths:
    if path := os.getenv("BOT_PATH"):
        return Paths(Path(path))
    return Paths(Path(__file__).parent.parent.parent)

# Загружаем конфигурацию
paths = get_paths()
config = load_config(paths)

# Создаем движок базы данных
engine = create_async_engine(config.db.uri, echo=True)

# Создаем базовый класс для моделей
Base = declarative_base()

# Импортируем модели (должны быть после объявления Base)
from .user import User
from .chat import Chat
from .parsed_rate import ParsedRate

# Создаем фабрику сессий
async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

def create_pool(db_config=None):
    """Создает пул сессий (для обратной совместимости)"""
    if db_config:
        # Если передана конфигурация, создаем движок на ее основе
        temp_engine = create_async_engine(db_config.uri, echo=True)
        return sessionmaker(temp_engine, class_=AsyncSession, expire_on_commit=False)
    return async_session_maker

# Экспортируем необходимые объекты
__all__ = ['Base', 'engine', 'create_pool', 'async_session_maker', 'User', 'Chat', 'ParsedRate']