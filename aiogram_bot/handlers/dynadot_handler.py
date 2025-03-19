import ssl
import aiohttp
import os
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import FSInputFile, CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")

router = Router()

API_URL = "https://api.dynadot.com/api3.json"
INPUT_FILE = "../file_parser/urls_to_check.txt"  # Мой файл с доменами
OUTPUT_FILE = "../file_parser/available_domains.txt"  # Сюда запишем доступные домены
UPLOAD_DIR = "../file_parser/uploads"  # Папка для загруженных файлов
os.makedirs(UPLOAD_DIR, exist_ok=True)  # Создаём папку, если её нет


class DomainStates(StatesGroup):
    WaitingForConfirmation = State()
    WaitingForFile = State()
    Processing = State()


# ✅ Проверка доступности домена
async def check_domain_availability(domain, session):
    params = {"key": API_KEY, "command": "search", "domain0": domain, "show_price": "1"}

    try:
        async with session.get(API_URL, params=params) as response:
            text = await response.text()
            print(f"Ответ для {domain}: {text}")

            if '"Available":"yes"' in text:
                price_str = text.split("Registration Price:")[1].split("in USD")[0].strip()
                price = float(price_str)
                if price <= 4:
                    print(f"✅ Домен {domain} доступен за {price} USD")
                    return f"{domain} {price}\n"
            elif '"Available":"no"' in text:
                print(f"❌ Домен {domain} недоступен.")
            else:
                print(f"⚠️ Неизвестный статус для {domain}. Ответ: {text}")
    except Exception as e:
        print(f"⚠️ Ошибка при запросе для {domain}: {e}")

    return None


# 📝 Обработка доменов из файла
async def process_domains(file_path):
    if not os.path.exists(file_path):
        print("❌ Файл не найден")
        return None

    available_domains = []

    try:
        # Создаём SSL контекст для отключения проверки сертификатов
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl_context=ssl_context)) as session:
            with open(file_path, "r") as file:
                for domain in file:
                    domain = domain.strip()
                    if domain:
                        result = await check_domain_availability(domain, session)
                        if result:
                            available_domains.append(result)

        if available_domains:
            with open(OUTPUT_FILE, "w") as file:
                file.writelines(available_domains)
            print(f"✅ Результаты сохранены в {OUTPUT_FILE}")
            return OUTPUT_FILE

    except Exception as e:
        print(f"⚠️ Ошибка при обработке доменов: {e}")

    return None


# 🕹️ Обработка нажатия кнопки "Да"
@router.callback_query(F.data == "yes_dynadot")
async def handle_yes_dynadot(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer("⏳ Начинаю обработку...")

    file_path = await process_domains(INPUT_FILE)

    if file_path:
        buttons = [
            [InlineKeyboardButton(text="Да", callback_data="yes_dynadot_pay")],
            [InlineKeyboardButton(text="Нет", callback_data="no_dynadot_pay")],
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        file = FSInputFile(file_path)
        await callback_query.message.answer_document(
            file, caption="✅ Доступные домены для покупки:\n- Хочешь их выкупить? Жми <b>[Да]</b>\n"
                          "- Хочешь отредактировать файл? Жми <b>[Нет]</b> и кидай файл.",
            reply_markup=keyboard, parse_mode="HTML"
        )
        await state.set_state(DomainStates.WaitingForConfirmation)
    else:
        await callback_query.message.answer("❌ Доступные домены не найдены.")
        await state.clear()


# 🕹️ Обработка нажатия кнопки "Нет" → ждем файл
@router.callback_query(F.data == "no_dynadot")
async def handle_no_dynadot(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer("📂 Отправь файл с доменами (.txt)")
    await state.set_state(DomainStates.WaitingForFile)


# 📥 Загрузка файла
@router.message(DomainStates.WaitingForFile, F.document)
async def handle_file_upload(message: Message, state: FSMContext):
    file_name = message.document.file_name

    if not file_name.endswith(".txt"):
        await message.answer("❌ Нужно отправить текстовый файл (.txt)")
        return

    file_path = os.path.join(UPLOAD_DIR, file_name)
    try:
        await message.bot.download(message.document.file_id, file_path)
        await message.answer("⏳ Обрабатываю загруженный файл...")
    except Exception as e:
        await message.answer(f"❌ Ошибка при загрузке файла: {e}")
        return

    processed_file = await process_domains(file_path)

    if processed_file:
        buttons = [
            [InlineKeyboardButton(text="Да", callback_data="yes_dynadot_pay")],
            [InlineKeyboardButton(text="Нет", callback_data="no_dynadot_pay")],
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        file = FSInputFile(processed_file)
        await message.answer_document(
            file, caption="✅ Доступные домены для покупки:\n- Хочешь их выкупить? Жми <b>[Да]</b>\n"
                          "- Хочешь отредактировать файл? Жми <b>[Нет]</b> и кидай файл.",
            reply_markup=keyboard, parse_mode="HTML"
        )
        await state.set_state(DomainStates.WaitingForConfirmation)
    else:
        await message.answer("❌ В файле нет доступных доменов.")
        await state.clear()
