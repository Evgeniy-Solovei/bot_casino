# Используем базовый образ Python 3.12 с поддержкой Chrome и chromedriver
FROM python:3.12

# Устанавливаем рабочий каталог
WORKDIR /bot_core

# Устанавливаем часовой пояс Europe/Moscow
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Устанавливаем Chrome и chromedriver
RUN apt-get update && \
    apt-get install -y wget unzip gnupg curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Устанавливаем Chrome
RUN wget -q -O google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get update && \
    apt-get install -y ./google-chrome.deb && \
    rm google-chrome.deb

# Устанавливаем совместимый ChromeDriver
ENV CHROME_VERSION=133.0.6943.126
RUN wget -O /tmp/chromedriver-linux64.zip https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip && \
    unzip /tmp/chromedriver-linux64.zip -d /usr/local/bin/ && \
    mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver-linux64.zip /usr/local/bin/chromedriver-linux64

# Устанавливаем зависимости Python
COPY requirements.txt .
RUN pip install -r requirements.txt

# Копируем проект
COPY . .

# Открываем порт
EXPOSE 8000

# Запускаем миграции, сервер и бота одновременно
CMD ["sh", "-c", "python manage.py migrate && uvicorn bot_core.asgi:application --host 0.0.0.0 --port 8000 & python tg_bot.py"]
