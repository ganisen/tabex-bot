# 🚭 Табекс-бот

Telegram бот для помощи в отказе от курения с персонажами из произведений Терри Пратчетта.

## 🚀 Быстрый старт с Docker

### Системные требования

- Docker Desktop (Windows/Mac) или Docker Engine (Linux)
- Docker Compose v2.0+
- Git

### Запуск на новом компьютере

1. **Клонирование репозитория**
```bash
git clone <your-repository-url>
cd tabex-bot
```

2. **Настройка переменных окружения**
```bash
# Скопируйте пример конфигурации
cp .env.example .env

# Отредактируйте .env файл и укажите ваш BOT_TOKEN
# Получить токен можно у @BotFather в Telegram
```

3. **Запуск приложения**
```bash
# Сборка и запуск в production режиме
docker-compose up -d

# Или запуск в development режиме с логами
docker-compose --profile dev up tabex-bot-dev
```

4. **Проверка работы**
```bash
# Просмотр логов
docker-compose logs -f tabex-bot

# Проверка статуса контейнера
docker-compose ps
```

## 📝 Доступные команды

### Production режим
```bash
# Запуск в фоновом режиме
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Просмотр логов
docker-compose logs -f tabex-bot

# Обновление (после git pull)
docker-compose build --no-cache
docker-compose up -d
```

### Development режим
```bash
# Запуск с hot reload и подробными логами
docker-compose --profile dev up tabex-bot-dev

# Остановка dev режима
docker-compose --profile dev down
```

## 🔧 Конфигурация

### Переменные окружения (.env файл)

```env
# Обязательные параметры
BOT_TOKEN='your_telegram_bot_token'    # Токен от @BotFather
DATABASE_PATH='data/tabex_bot.db'      # Путь к базе данных
LOG_LEVEL='INFO'                       # Уровень логирования

# Опциональные параметры
TZ='Europe/Moscow'                     # Часовой пояс
```

### Структура проекта
```
tabex-bot/
├── data/                   # База данных и пользовательские данные
│   └── tabex_bot.db       # SQLite база данных
├── logs/                   # Логи приложения (создается автоматически)
├── core/                   # Основной код приложения
├── config/                 # Конфигурационные файлы
├── docker-compose.yaml     # Docker Compose конфигурация
├── Dockerfile             # Docker образ
├── .env.example           # Пример переменных окружения
└── requirements.txt       # Python зависимости
```

## 🐳 Docker детали

### Особенности Docker конфигурации

- **Мультистейдж сборка**: Оптимизированный образ без dev зависимостей
- **Непривилегированный пользователь**: Повышенная безопасность
- **Постоянные тома**: Данные сохраняются между перезапусками
- **Ограничения ресурсов**: 256MB RAM, 0.5 CPU limit
- **Health checks**: Автоматическая проверка состояния контейнера
- **Ротация логов**: Автоматическая очистка старых логов

### Управление данными

```bash
# Резервное копирование базы данных
docker-compose exec tabex-bot cp /app/data/tabex_bot.db /app/data/backup_$(date +%Y%m%d).db

# Очистка логов
docker-compose exec tabex-bot sh -c "truncate -s 0 /app/tabex_bot.log"

# Доступ к контейнеру для отладки
docker-compose exec tabex-bot bash
```

## 🛠 Разработка

### Локальная разработка без Docker
```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\\Scripts\\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
cp .env.example .env
# Отредактируйте .env файл

# Запуск
python main.py
```

### Сборка Docker образа вручную
```bash
# Сборка образа
docker build -t tabex-bot:latest .

# Запуск контейнера
docker run -d \
  --name tabex-bot \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  tabex-bot:latest
```

## 📋 Устранение неполадок

### Частые проблемы

1. **Контейнер не запускается**
```bash
# Проверьте логи
docker-compose logs tabex-bot

# Проверьте переменные окружения
docker-compose config
```

2. **База данных не создается**
```bash
# Проверьте права доступа к директории data
ls -la data/

# Создайте директорию вручную если нужно
mkdir -p data logs
```

3. **Бот не отвечает**
```bash
# Проверьте корректность BOT_TOKEN в .env файле
# Убедитесь что бот активен у @BotFather
```

### Полная очистка

```bash
# Остановка и удаление контейнеров
docker-compose down -v

# Удаление образов
docker rmi tabex-bot:latest

# Очистка неиспользуемых ресурсов
docker system prune -a
```

## 📄 Лицензия

Этот проект использует материалы произведений Терри Пратчетта в образовательных и развлекательных целях.

## 🤝 Поддержка

Для вопросов и проблем создайте issue в репозитории проекта.
