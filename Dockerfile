# Мультистейдж Docker сборка для Табекс-бота
FROM python:3.11-slim as builder

# Установка системных зависимостей для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Создание виртуального окружения
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копирование и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Финальный образ
FROM python:3.11-slim

# Установка runtime зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя для безопасности
RUN groupadd -r tabexbot && useradd -r -g tabexbot tabexbot

# Копирование виртуального окружения из builder стейдж
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Установка рабочей директории
WORKDIR /app

# Копирование исходного кода приложения
COPY --chown=tabexbot:tabexbot . .

# Создание директорий для данных и логов
RUN mkdir -p /app/data /app/logs \
    && chown -R tabexbot:tabexbot /app

# Переключение на непривилегированного пользователя
USER tabexbot

# Установка переменных окружения по умолчанию
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/tabex_bot.db
ENV LOG_LEVEL=INFO

# Здоровье контейнера
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; import sys; sys.exit(0)" || exit 1

# Открытие портов (если нужно для webhook'ов)
# EXPOSE 8443

# Команда запуска
CMD ["python", "main.py"]
