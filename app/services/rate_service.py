from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.rate import CurrentRate
import logging

logger = logging.getLogger(__name__)


class RateService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_current_rate(self) -> float:
        """Возвращает текущий курс из БД"""
        try:
            query = select(CurrentRate).order_by(CurrentRate.last_updated.desc())
            current_rate = await self.session.scalar(query)

            if current_rate:
                return current_rate.rate_value
            else:
                # Если курса нет - создаем начальный
                initial_rate = CurrentRate(rate_value=0.0, last_admin_id=1)
                self.session.add(initial_rate)
                await self.session.commit()
                return 0.0

        except Exception as e:
            logger.error(f"Error getting current rate: {e}")
            return 0.0

    async def update_rate(self, new_rate: float, admin_id: int) -> bool:
        """Обновляет текущий курс"""
        try:
            # Создаем новую запись (история сохраняется)
            updated_rate = CurrentRate(
                rate_value=new_rate,
                last_admin_id=admin_id
            )
            self.session.add(updated_rate)
            await self.session.commit()

            logger.info(f"Rate updated to {new_rate} by admin {admin_id}")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating rate: {e}")
            return False

    async def format_rate_message(self) -> str:
        """Форматирует сообщение для табло"""
        current_rate = await self.get_current_rate()

        if current_rate == 0.0:
            return "🏦 Курс пока не установлен\n\nОжидайте обновления..."
        else:
            return f"🏦 Текущий курс: {current_rate} RUB\n\nНажмите 'Обновить курс' для актуализации"