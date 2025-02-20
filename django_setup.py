import os
import django

# Укажите путь к вашему settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bot_core.settings')

# Настройка Django
django.setup()
