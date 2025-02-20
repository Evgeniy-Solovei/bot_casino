# Используем базовый образ Python 3.12
FROM python:3.12

# Команда для вывода логов в консоле
ENV PYTHONUNBUFFERED=1

# Устанавливаем рабочий каталог
WORKDIR /bot_core

# Копируем файл requirements.txt
COPY requirements.txt requirements.txt

# Экспортируем порт, который будет использоваться для доступа к приложению
EXPOSE 8000

# Устанавливаем часовой пояс Europe/Moscow
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Устанавливаем зависимости из файла requirements.txt без кэша
RUN pip install --no-cache-dir -r requirements.txt

# Копируем файлы и папки из папки CRM_system в рабочий каталог WORKDIR
COPY bot_core .

# Запускаем сервер + бот
CMD ["sh", "-c", "uvicorn bot_core.asgi:application --host 0.0.0.0 --port 8000 && python tg_bot.py"]
