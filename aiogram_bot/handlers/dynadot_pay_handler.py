import os
import aiohttp
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from django.db import transaction
from dotenv import load_dotenv

from bot.models import PurchasedDomain

load_dotenv()
API_KEY = os.getenv("API_KEY")

API_URL = "https://api.dynadot.com/api3.json"
UPLOAD_DIR = "uploads"
OUTPUT_FILE = "purchased_domains.txt"

router = Router()


class DomainStates(StatesGroup):
    WaitingForConfirmation = State()
    WaitingForFile = State()
    ProcessingPurchase = State()


# ✅ Покупка доменов через API и сохранение в БД
async def purchase_domains(domains, session):
    purchased = []
    for i in range(0, len(domains), 99):
        chunk = domains[i:i + 99]
        params = {"key": API_KEY, "command": "bulk_register"}
        params.update({f"domain{idx}": domain for idx, domain in enumerate(chunk)})

        try:
            async with session.get(API_URL, params=params) as response:
                data = await response.json()
                if data.get("ResponseCode") == "0":
                    purchased.extend(chunk)
        except Exception as e:
            print(f"⚠️ Ошибка при покупке доменов: {e}")

    # Сохранение в БД
    async with transaction.atomic():
        for domain in purchased:
            await PurchasedDomain.objects.acreate(domain=domain)

    return purchased


# 🕹️ Обработка нажатия кнопки "Да" → Покупка доменов
@router.callback_query(F.data == "yes_dynadot_pay")
async def handle_yes_dynadot_pay(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("💳 Покупаю домены...")

    file_path = os.path.join(UPLOAD_DIR, "available_domains.txt")
    if not os.path.exists(file_path):
        await callback_query.message.answer("❌ Файл с доменами не найден.")
        return

    with open(file_path, "r") as file:
        domains = [line.strip() for line in file if line.strip()]

    if not domains:
        await callback_query.message.answer("❌ Нет доменов для покупки.")
        return

    async with aiohttp.ClientSession() as session:
        purchased = await purchase_domains(domains, session)

    if purchased:
        with open(OUTPUT_FILE, "w") as file:
            file.writelines(f"{domain}\n" for domain in purchased)
        file = FSInputFile(OUTPUT_FILE)
        await callback_query.message.answer_document(file, caption="✅ Купленные домены сохранены.")
    else:
        await callback_query.message.answer("❌ Не удалось купить домены.")

    await state.clear()


# 🕹️ Обработка нажатия кнопки "Нет" → Ждем новый файл
@router.callback_query(F.data == "no_dynadot_pay")
async def handle_no_dynadot_pay(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("📂 Загрузите новый файл с доменами.")
    await state.set_state(DomainStates.WaitingForFile)


# 📥 Загрузка и обработка нового файла
@router.message(DomainStates.WaitingForFile, F.document)
async def handle_file_upload(message: Message, state: FSMContext):
    file_name = message.document.file_name

    if not file_name.endswith(".txt"):
        await message.answer("❌ Нужно загрузить .txt файл.")
        return

    file_path = os.path.join(UPLOAD_DIR, file_name)
    await message.bot.download(message.document.file_id, file_path)

    await message.answer("⏳ Обрабатываю файл...")

    with open(file_path, "r") as file:
        domains = [line.strip() for line in file if line.strip()]

    if domains:
        buttons = [
            [InlineKeyboardButton(text="Да", callback_data="yes_dynadot_pay")],
            [InlineKeyboardButton(text="Нет", callback_data="no_dynadot_pay")],
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(
            "✅ Файл загружен. Хотите сразу купить домены?", reply_markup=keyboard
        )
        await state.set_state(DomainStates.WaitingForConfirmation)
    else:
        await message.answer("❌ Файл пуст или содержит некорректные данные.")
        await state.clear()
