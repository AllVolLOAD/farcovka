from aiogram import BaseMiddleware
from typing import Dict, Any, Callable, Awaitable
from app.dao.holder import HolderDao
from app.services.dashboard_sevice import DashboardService
from app.services.rapira_parser_service import RapiraParserService
from app.services.parser_service import ParserService


class ServicesMiddleware(BaseMiddleware):
    def __init__(self, session_pool):
        self.session_pool = session_pool

    async def __call__(
            self,
            handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: Dict[str, Any]
    ) -> Any:
        async with self.session_pool() as session:
            # Создаем HolderDao
            dao = HolderDao(session)

            # Создаем сервисы
            dashboard_service = DashboardService(session)
            parser_service = ParserService(dao)
            rapira_parser_service = RapiraParserService(dao)  # Добавляем создание сервиса

            # Добавляем сервисы в data
            data['dashboard_service'] = dashboard_service
            data['parser_service'] = parser_service
            data['rapira_parser_service'] = rapira_parser_service  # Добавляем в data

            return await handler(event, data)