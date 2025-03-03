import asyncio
import os
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram_bot.parser.parser_rkn import search_site, OUTPUT_FILE


router = Router()


class SearchState(StatesGroup):
    waiting_for_query = State()


@router.message(Command("search"))
async def process_search(message: types.Message, state: FSMContext):
    await message.reply("🔍 Введите домен или URL для поиска:")
    await state.set_state(SearchState.waiting_for_query)


@router.message(SearchState.waiting_for_query)
async def handle_user_query(message: types.Message, state: FSMContext):
    user_query = message.text.strip()
    if not user_query:
        await message.reply("❌ Вы не ввели запрос. Попробуйте снова.")
        return
    await message.reply(f"🔍 Запрос '{user_query}' принят. Обрабатываем данные...")
    try:
        await asyncio.to_thread(search_site, user_query, max_pages=20)
    except Exception as e:
        await message.reply(f"⚠️ Произошла ошибка при поиске: {e}")
        await state.clear()
        return

    if not os.path.exists(OUTPUT_FILE):
        await message.reply("❌ Не удалось найти файл с результатами. Попробуйте позже.")
        await state.clear()
        return

    if os.path.getsize(OUTPUT_FILE) == 0:
        await message.reply("❌ Файл результатов пуст. Вероятно, ничего не найдено.")
        await state.clear()
        return

    try:
        file = FSInputFile(OUTPUT_FILE)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="yes_dynadot")],
            [InlineKeyboardButton(text="Нет", callback_data="no_dynadot")]
        ])
        await message.answer_document(
            file,
            caption="✅ <b>Вот что я смог найти из разблокированных доменов.</b>\n\n"
                    "- Хочешь проверить что можно купить Dynadot? Жми <b>[Да]</b>.\n"
                    "- Хочешь отредактировать файл? Жми <b>[Нет]</b> и кидай файл.",
            reply_markup=keyboard, parse_mode="HTML"
        )
    except Exception as e:
        await message.reply(f"⚠️ Ошибка при отправке файла: {e}")
    finally:
        await state.clear()

