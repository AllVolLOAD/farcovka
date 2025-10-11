from app.dao import UserDAO
from app.models.dto.user import UserCreate, UserInDB  # Используем новые классы

async def upsert_user(user: UserCreate, user_dao: UserDAO) -> UserInDB:
    saved_user = await user_dao.upsert_user(user)
    await user_dao.commit()
    return saved_user