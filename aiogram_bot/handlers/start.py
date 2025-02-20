from aiogram import types, Router
from aiogram.filters import CommandStart

router = Router()


@router.message(CommandStart())
async def start_command(message: types.Message):
    help_text = (
        "Привет! Я бот для поиска доменов. Вот что я могу:\n\n"
        "/start - Начать заново\n"
        "/search <домен> - Поиск на РКН по разблокированным доменам или URL\n"
        "/domains - Список купленных доменных имен"
    )
    await message.reply(help_text)
