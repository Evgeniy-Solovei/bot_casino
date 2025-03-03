from aiogram.types import BotCommand

import django_setup
import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram_bot.handlers import start, search_handler, dynadot_handler, dynadot_pay_handler
from dotenv import load_dotenv
from selenium import webdriver


load_dotenv()
TOKEN = os.getenv("TOKEN")
logging.basicConfig(level=logging.INFO)


bot = Bot(token=TOKEN)
dp = Dispatcher()

# Настройка браузера (Chrome)
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(options=chrome_options)


async def set_commands():
    commands = [
        BotCommand(command="/start", description="Начать заново"),
        BotCommand(command="/search", description="Поиск на РКН"),
        BotCommand(command="/domains", description="Список доменов")
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    logging.info("Бот успешно запущен.")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await set_commands()
        await dp.start_polling(bot)  # Запуск бота
    finally:
        if driver:
            driver.quit()  # Закрываем браузер при завершении работы
            logging.info("Браузер закрыт. Бот остановлен.")


if __name__ == "__main__":
    dp.include_routers(start.router)
    dp.include_routers(search_handler.router)
    dp.include_routers(dynadot_handler.router)
    dp.include_routers(dynadot_pay_handler.router)

    asyncio.run(main())
