import os
import ssl
import aiohttp
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv
from bot.models import PurchasedDomain

load_dotenv()
API_KEY = os.getenv("API_KEY")

API_URL = "https://api.dynadot.com/api3.json"
UPLOAD_DIR = "../file_parser/"
OUTPUT_FILE = "purchased_domains.txt"

router = Router()


class DomainPayStates(StatesGroup):
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
            # Создаём SSL контекст для отключения проверки сертификатов
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # Открытие сессии с созданным SSL контекстом
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl_context=ssl_context)) as session:
                async with session.get(API_URL, params=params) as response:
                    data = await response.json()
                    if data.get("ResponseCode") == "0":
                        purchased.extend(chunk)
        except Exception as e:
            print(f"⚠️ Ошибка при покупке доменов: {e}")

    # Сохранение в БД
    purchased_domains = [PurchasedDomain(domain=domain) for domain in purchased]
    await PurchasedDomain.objects.abulk_create(purchased_domains)

    return purchased


# 🕹️ Обработка нажатия кнопки "Да" → Покупка доменов
@router.callback_query(F.data == "yes_dynadot_pay")
async def handle_yes_dynadot_pay(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer("💳 Покупаю домены...")

    file_path = os.path.join(UPLOAD_DIR, "available_domains.txt")
    if not os.path.exists(file_path):
        await callback_query.message.answer("❌ Файл с доменами не найден.")
        return

    try:
        with open(file_path, "r") as file:
            domains = [line.strip().split()[0] for line in file if line.strip()]
    except Exception as e:
        await callback_query.message.answer(f"❌ Ошибка при обработке файла: {e}")
        return

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
    await callback_query.answer()
    await callback_query.message.answer("📂 Загрузите новый файл с доменами.")
    await state.set_state(DomainPayStates.WaitingForFile)


# 📥 Загрузка и обработка нового файла
@router.message(DomainPayStates.WaitingForFile, F.document)
async def handle_file_upload(message: Message, state: FSMContext):
    file_name = message.document.file_name
    if not file_name.endswith(".txt"):
        await message.answer("❌ Нужно загрузить .txt файл.")
        return

    file_path = os.path.join(UPLOAD_DIR, file_name)
    try:
        await message.bot.download(message.document.file_id, file_path)
    except Exception as e:
        await message.answer(f"❌ Ошибка при загрузке файла: {e}")
        return

    await message.answer("⏳ Обрабатываю файл...")

    try:
        with open(file_path, "r") as file:
            domains = [line.strip().split()[0] for line in file if line.strip()]
    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке файла: {e}")
        return

    if domains:
        # Покупка доменов через API
        async with aiohttp.ClientSession() as session:
            purchased = await purchase_domains(domains, session)

        if purchased:
            # Сохранение в БД
            purchased_domains = [PurchasedDomain(domain=domain) for domain in purchased]
            await PurchasedDomain.objects.abulk_create(purchased_domains)

            # Сохранение купленных доменов в файл
            with open(OUTPUT_FILE, "w") as file:
                file.writelines(f"{domain}\n" for domain in purchased)

            # Отправка документа с купленными доменами
            file = FSInputFile(OUTPUT_FILE)
            await message.answer_document(file, caption="✅ Купленные домены сохранены.")
        else:
            await message.answer("❌ Не удалось купить домены.")
    else:
        await message.answer("❌ Файл пуст или содержит некорректные данные.")
    await state.clear()
