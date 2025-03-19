import logging

from aiogram import Router, types
from aiogram.filters import Command
from bot.models import PurchasedDomain
from django.utils import timezone

router = Router()


@router.message(Command("domains"))
async def handle_domains_command(message: types.Message):
    try:
        # Получаем все домены из базы данных
        domains = PurchasedDomain.objects.order_by('-purchased_at')

        if not await domains.aexists():
            await message.answer("🛑 Список доменов пуст.")
            return

        # Формируем сообщение с доменами и датами
        response = "📋 Список приобретенных доменов:\n\n"
        async for domain in domains.aiterator():
            # Форматируем дату в удобный формат
            purchased_date = timezone.localtime(domain.purchased_at).strftime("%d.%m.%Y")
            response += f"• {domain.domain} (куплен: {purchased_date})\n"

        await message.answer(response)

    except Exception as e:
        logging.error(f"Ошибка при обработке команды /domains: {str(e)}")
        await message.answer("⚠️ Произошла ошибка при получении списка доменов.")
