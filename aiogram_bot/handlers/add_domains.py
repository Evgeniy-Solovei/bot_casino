from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.types import Message
from django.utils.timezone import now
import re
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram_bot.handlers.dynadot_pay_handler import create_cloudflare_zone, set_nameservers, API_KEY
from bot.models import PurchasedDomain

router = Router()
DOMAIN_REGEX = re.compile(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Состояния для FSM
class AddDomainsState(StatesGroup):
    # Состояние ожидания ввода доменов
    waiting_for_domains = State()  # Состояние ожидания ввода доменов или файла

# Обработчик команды /add_domains
@router.message(Command("add_domains"))
async def add_domains_command(message: Message, state: FSMContext):
    # Запрашиваем у пользователя ввод доменов или отправку файла
    await message.answer(
        "Введите доменные имена через пробел или отправьте файл с доменами (каждый на новой строке)."
    )
    # Устанавливаем состояние ожидания
    await state.set_state(AddDomainsState.waiting_for_domains)

# Обработчик ввода доменов или файла
@router.message(AddDomainsState.waiting_for_domains, F.text | F.document)
async def process_domains_input(message: Message, state: FSMContext):
    domains_to_add = set()

    # Если пользователь ввел текст
    if message.text:
        # Извлекаем домены из текста сообщения
        domains_to_add = {d.strip().lower() for d in message.text.split() if DOMAIN_REGEX.match(d.strip())}

    # Если пользователь отправил файл
    elif message.document:
        file = await message.bot.get_file(message.document.file_id)
        file_content = await message.bot.download_file(file.file_path)
        # Читаем домены из файла
        domains_to_add = {line.strip().lower() for line in file_content.read().decode("utf-8").splitlines() if DOMAIN_REGEX.match(line.strip())}

    # Если домены не найдены
    if not domains_to_add:
        await message.answer("⚠️ Не найдено корректных доменных имен.")
        await state.clear()  # Сбрасываем состояние
        return

    # Ищем уже существующие домены (асинхронно)
    existing_domains = set()
    async for domain in PurchasedDomain.objects.filter(domain__in=domains_to_add).aiterator():
        existing_domains.add(domain.domain)

    new_domains = domains_to_add - existing_domains

    # Добавляем только новые домены
    if new_domains:
        await PurchasedDomain.objects.abulk_create([PurchasedDomain(domain=d, purchased_at=now()) for d in new_domains])

        # Просто прогоняем каждый домен через API без сохранения результатов
        for domain in new_domains:
            try:
                nameservers = await create_cloudflare_zone(domain)
                if nameservers:
                    await set_nameservers(domain, API_KEY, nameservers[0], nameservers[1])
            except Exception as e:
                await message.answer(f"⚠️ Ошибка при обработке домена {domain}: {str(e)}")
                continue

        await message.answer(f"✅ Добавлены домены:\n" + "\n".join(new_domains))
    else:
        await message.answer("⚠️ Все домены уже есть в БД.")

    await state.clear()
