import logging
from aiogram.filters import BaseFilter
from aiogram.types import Message

logger = logging.getLogger(__name__)

class IsSuperuser(BaseFilter):
    def __init__(self, superusers):
        logger.info(f"🔧 IsSuperuser filter initialized with: {superusers} (type: {type(superusers)})")
        self.superusers = superusers

    async def __call__(self, message: Message) -> bool:
        try:
            user_id = message.from_user.id
            result = user_id in self.superusers
            logger.info(f"🔍 Superuser check: user_id={user_id}, superusers={self.superusers}, result={result}")
            return result
        except Exception as e:
            logger.error(f"❌ Superuser filter error: {e}")
            logger.error(f"🔍 User ID: {message.from_user.id}, Superusers type: {type(self.superusers)}")
            return False

# Добавим также простую функцию для теста
def is_superuser(message: Message, superusers) -> bool:
    logger.info(f"🔧 is_superuser function called with superusers: {superusers}")
    return message.from_user.id in superusers


import logging
from aiogram.filters import BaseFilter
from aiogram.types import Message

logger = logging.getLogger(__name__)

class SuperuserFilter(BaseFilter):
    def __init__(self, superusers):
        logger.info(f"🔧 SuperuserFilter initialized with: {superusers} (type: {type(superusers)})")
        self.superusers = superusers

    async def __call__(self, message: Message) -> bool:
        try:
            user_id = message.from_user.id
            result = user_id in self.superusers
            logger.info(f"🔍 Superuser check: user_id={user_id}, superusers={self.superusers}, result={result}")
            return result
        except Exception as e:
            logger.error(f"❌ Superuser filter error: {e}")
            logger.error(f"🔍 User ID: {message.from_user.id}, Superusers type: {type(self.superusers)}")
            return False
