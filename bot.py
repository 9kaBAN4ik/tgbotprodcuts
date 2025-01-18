from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, ReplyKeyboardMarkup, KeyboardButton,Message
import asyncio
import logging
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import TOKEN
from handlers import (
    start_handler,
    balance_handler,
    add_product_handler,
)
from handlers.referrals import referral_router  # Хэндлер для реферальной системы
from handlers.menu_handler import back_to_main_menu
from database import initialize_db
from admin import router as admin_router  # Подключаем админский маршрутизатор
from handlers.info_handler import router as info_router
from handlers.personal_info import router as myinfo
from handlers.menu_handler import router as menurouter
from handlers.partner_handler import router as partnerrouter
# Настроим логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/menu", description="Показать главное меню")
    ]
    await bot.set_my_commands(commands)

@dp.message(Command(commands=["menu"]))
async def show_main_menu(message: Message, state: FSMContext):
    await back_to_main_menu(message, state)


async def main():
    logger.info("Запуск бота...")
    await set_commands(bot)

    # Подключаем все маршрутизаторы
    dp.include_router(start_handler.router)
    dp.include_router(balance_handler.router)
    dp.include_router(add_product_handler.router)
    dp.include_router(referral_router)  # Подключаем реферальную систему
    dp.include_router(info_router)
    dp.include_router(admin_router)  # Подключаем админский роутер
    dp.include_router(myinfo)
    dp.include_router(menurouter)
    dp.include_router(partnerrouter)
    logger.info("Начинаем polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    initialize_db()
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Бот остановлен!")
