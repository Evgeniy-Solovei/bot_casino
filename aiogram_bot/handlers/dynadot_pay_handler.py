import asyncio
import json
import os
import ssl
import aiohttp
import httpx
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
OUTPUT_FILE = "../file_parser/purchased_domains.txt"

router = Router()


class DomainPayStates(StatesGroup):
    WaitingForConfirmation = State()
    WaitingForFile = State()
    ProcessingPurchase = State()


async def create_cloudflare_zone(domain_name: str) -> list[str] | None:
    """Создание зоны в Cloudflare и получение NS"""
    print(f"📤 Отправка запроса на создание зоны для домена: {domain_name}")

    headers = {
        "X-Auth-Email": "odin.vin@yandex.ru",
        "X-Auth-Key": "625a435d54464faa61c5fdf7360adade9e828",
        "Content-Type": "application/json",
    }
    data = {
        "name": domain_name,
        "jump_start": True,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.cloudflare.com/client/v4/zones",
                json=data,
                headers=headers,
            )
        except Exception as e:
            print(f"💥 Ошибка при попытке отправить запрос: {e}")
            return None

        print(f"📩 Ответ от Cloudflare: статус {response.status_code}")
        print(f"📄 Тело ответа: {response.text}")
        print(f"🧾 Заголовки ответа:")
        for k, v in response.headers.items():
            print(f"   {k}: {v}")

        if response.status_code == 200:
            res_json = response.json()
            if res_json.get("success"):
                nameservers = res_json["result"].get("name_servers")
                print(f"✅ Зона {domain_name} создана. NS: {nameservers}")
                return nameservers
            else:
                print(f"⚠️ Не удалось создать зону (ответ без success): {res_json}")
        elif response.status_code == 429:
            print("🚫 Превышен лимит запросов! Подожди немного или уменьшай частоту запросов.")
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                print(f"⏱ Сервер просит подождать: {retry_after} секунд.")
        else:
            print(f"❌ Ошибка при создании зоны: {response.status_code} — {response.text}")

    print("🔚 Возвращаю None, зона не создана.")
    return None


async def send_domain_status_to_api(domain_name, status="Не Активен"):
    """Отправка статуса домена"""
    url = "https://api.gang-soft.com/api/take_bot_data/"
    payload = {
        "current_domain": domain_name,
        "domain_mask": domain_name,
        "status": status
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.post(url, data=payload, headers=headers) as response:
                response_text = await response.text()
                if response.status == 200:
                    print(f"✔️ Домен {domain_name} успешно отправлен на сервер.")
                else:
                    print(f"❌ Ошибка {response.status}: {response_text}")
        except Exception as e:
            print(f"⚠️ Ошибка при отправке данных домена {domain_name}: {e}")


async def set_nameservers(domain: str, api_key: str, ns1: str, ns2: str):
    """Установка NS через Dynadot"""
    API_URL_SET = "https://api.dynadot.com/api3.json"

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    for attempt in range(3):
        try:
            params = {
                "key": api_key,
                "command": "set_ns",
                "domain": domain,
                "ns1": ns1,
                "ns2": ns2
            }

            headers = {"Accept": "application/json"}

            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
                async with session.get(API_URL_SET, params=params, headers=headers) as response:
                    raw_data = await response.text()
                    try:
                        data = json.loads(raw_data)
                    except json.JSONDecodeError:
                        print(f"⚠️ Невалидный JSON от Dynadot при установке NS для {domain}:\n{raw_data}")
                        continue

                    response_data = data.get("SetNsResponse", {})
                    response_code = response_data.get("ResponseCode")

                    if str(response_code) == "0":
                        print(f"✅ Успешно установлены NS для {domain}")
                        return True
                    else:
                        error = response_data.get("Error", "Unknown error")
                        print(f"❌ Попытка {attempt + 1}: ошибка установки NS для {domain}: {error}")

        except Exception as e:
            print(f"🚨 Попытка {attempt + 1}: ошибка установки NS для {domain}: {str(e)}")

        if attempt < 2:
            wait = 5 * (attempt + 1)
            print(f"🔁 Повтор через {wait} секунд...")
            await asyncio.sleep(wait)

    print(f"❌ Все попытки установки NS для {domain} не увенчались успехом")
    return False

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
            # Открываем сессию с созданным SSL контекстом
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as temp_session:
                async with temp_session.get(API_URL, params=params) as response:
                    data = await response.json(content_type=None)
                    bulk_response = data.get("BulkRegisterResponse", {})
                    if bulk_response.get("ResponseCode") == 0 and bulk_response.get("Status") == "success":
                        bulk_register = bulk_response.get("BulkRegister", [])
                        for result in bulk_register:
                            domain_name = result.get("DomainName")
                            registration_result = result.get("Result")
                            message = result.get("Message")

                            if registration_result == "success":
                                purchased.append(domain_name)
                                # 1. Создаём зону в Cloudflare
                                nameservers = await create_cloudflare_zone(domain_name)
                                if nameservers:
                                    # 2. Устанавливаем NS у регистратора
                                    await set_nameservers(domain_name, API_KEY, nameservers[0], nameservers[1])
                                else:
                                    print(f"❗ NS для {domain_name} не получены, пропускаем установку NS.")

                                # Отправляем информацию на API после успешной регистрации
                                await send_domain_status_to_api(domain_name)
                            else:
                                print(f"❌ Ошибка при регистрации {domain_name}: {message}")
                    else:
                        print(f"❌ Ошибка при выполнении запроса: {bulk_response}")
        except Exception as e:
            print(f"⚠️ Ошибка при покупке доменов: {e}")
    # Сохранение в БД
    if purchased:
        purchased_domains = [PurchasedDomain(domain=domain) for domain in purchased]
        await PurchasedDomain.objects.abulk_create(purchased_domains, ignore_conflicts=True)
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
        # Отправляем каждый купленный домен на API
        for domain in purchased:
            await send_domain_status_to_api(domain)
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
            await PurchasedDomain.objects.abulk_create(purchased_domains, ignore_conflicts=True)

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
