from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv
import os


class DbConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = "Qazwsxedc1488"
    database: str = "facovka00"
    driver: str = "asyncpg"

    @property
    def uri(self) -> str:
        return f"postgresql+{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class BotConfig(BaseModel):
    token: str
    superusers: list[int] = [7111883883, 780245577]
    log_chat: Optional[int] = None


class Config(BaseModel):
    bot: BotConfig
    db: DbConfig


def load_config(paths) -> Config:
    """Загружает конфигурацию"""
    try:
        # Загружаем .env.prod
        env_file = paths.app_dir.parent / '.env.prod'
        load_dotenv(env_file)

        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            raise Exception(f"BOT_TOKEN не найден в {env_file}")

        return Config(
            bot=BotConfig(token=bot_token),
            db=DbConfig()
        )

    except Exception as e:
        raise Exception(f"Ошибка загрузки конфигурации: {e}")