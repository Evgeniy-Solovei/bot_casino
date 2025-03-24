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
    try:
        user_query = message.text.strip()
        if not user_query:
            await message.reply("❌ Пустой запрос. Введите текст для поиска.")
            return

        await message.reply(f"🔍 Начинаю поиск для: {user_query}...")

        # Запуск с таймаутом 5 минут
        await asyncio.wait_for(
            asyncio.to_thread(search_site, user_query, max_pages=5),
            timeout=300
        )

        if not os.path.exists(OUTPUT_FILE):
            await message.reply("❌ Файл результатов не найден")
            return

        file_size = os.path.getsize(OUTPUT_FILE)
        if file_size == 0:
            await message.reply("❌ Нет результатов для отображения")
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="yes_dynadot")],
            [InlineKeyboardButton(text="Нет", callback_data="no_dynadot")]
        ])

        await message.answer_document(
            FSInputFile(OUTPUT_FILE),
            caption="✅ Результаты поиска:\nПроверить доступность доменов?",
            reply_markup=keyboard
        )

    except asyncio.TimeoutError:
        await message.reply("🕒 Время выполнения поиска истекло")
    except Exception as e:
        await message.reply(f"⚠️ Ошибка: {str(e)}")
    finally:
        await state.clear()