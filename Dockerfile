# Используем базовый образ Python 3.12 с поддержкой Chrome и chromedriver
FROM python:3.12

# Устанавливаем рабочий каталог
WORKDIR /bot_core

# Устанавливаем часовой пояс Europe/Moscow
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Устанавливаем Chrome и chromedriver
RUN apt-get update && \
    apt-get install -y wget unzip gnupg && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    CHROME_DRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
    wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm /tmp/chromedriver.zip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# Открываем порт
EXPOSE 8000

# Запускаем миграции, сервер и бота одновременно
CMD ["sh", "-c", "python manage.py migrate && uvicorn bot_core.asgi:application --host 0.0.0.0 --port 8000 & python tg_bot.py"]