import django_setup
import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram_bot.handlers import start, search_handler, dynadot_handler, dynadot_pay_handler
from dotenv import load_dotenv


load_dotenv()
TOKEN = os.getenv("TOKEN")
logging.basicConfig(level=logging.INFO)


bot = Bot(token=TOKEN)
dp = Dispatcher()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    dp.include_routers(start.router)
    dp.include_routers(search_handler.router)
    dp.include_routers(dynadot_handler.router)
    dp.include_routers(dynadot_pay_handler.router)

    asyncio.run(main())
