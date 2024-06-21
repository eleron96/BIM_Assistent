# Используем официальный образ Python 3.12 в качестве базового
FROM python:3.12-slim

# Устанавливаем зависимости системы
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    sudo \
    systemd \
    systemd-sysv \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем pip и Poetry
RUN pip install --upgrade pip
RUN pip install poetry

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY pyproject.toml poetry.lock ./

# Отключаем создание виртуальных окружений и устанавливаем зависимости проекта
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev

# Устанавливаем specklepy через pip
RUN pip install specklepy
RUN pip install python-telegram-bot httpx

# Копируем все остальные файлы проекта
COPY . .

# Указываем команду, которая будет запускаться при старте контейнера
CMD ["poetry", "run", "python", "bot.py"]
