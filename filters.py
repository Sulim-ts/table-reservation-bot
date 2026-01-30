from aiogram.filters import BaseFilter
from aiogram.types import Message
from config import config
import logging

logger = logging.getLogger(__name__)


class IsAdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        user_id = message.from_user.id
        is_admin = user_id in config.ADMIN_IDS

        logger.info(f"User {user_id} (username: {message.from_user.username}) is admin: {is_admin}")
        logger.info(f"Admin IDs: {config.ADMIN_IDS}")

        return is_admin

