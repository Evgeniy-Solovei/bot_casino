from aiogram.types import BotCommand
import django_setup
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram_bot.handlers import start, search_handler, dynadot_handler, dynadot_pay_handler, domains
from dotenv import load_dotenv


load_dotenv()
TOKEN = os.getenv("TOKEN")
logging.basicConfig(level=logging.INFO)


bot = Bot(token=TOKEN)
dp = Dispatcher()

async def set_commands():
    commands = [
        BotCommand(command="/start", description="Начать заново"),
        BotCommand(command="/search", description="Поиск на РКН"),
        BotCommand(command="/check_domains", description="Проверить домены в Dynadot (прикрепите файл)"),
        BotCommand(command="/domains", description="Список доменов")
    ]
    await bot.set_my_commands(commands)

async def main() -> None:
    logging.info("Бот успешно запущен.")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await set_commands()
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка: {str(e)}")
    finally:
        logging.info("Бот остановен.")

if __name__ == "__main__":
    dp.include_routers(start.router)
    dp.include_routers(search_handler.router)
    dp.include_routers(dynadot_handler.router)
    dp.include_routers(dynadot_pay_handler.router)
    dp.include_routers(domains.router)
    asyncio.run(main())
