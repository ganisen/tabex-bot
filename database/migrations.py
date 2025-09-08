"""
Модуль миграций базы данных.

Содержит все SQL-скрипты для создания и обновления схемы базы данных.
Автоматически применяет необходимые миграции при запуске приложения.
"""
import logging
from database.connection import get_db

logger = logging.getLogger(__name__)


# SQL-скрипт создания таблицы пользователей
CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    username TEXT,
    gender TEXT CHECK(gender IN ('male', 'female')) NOT NULL,
    timezone TEXT DEFAULT 'Europe/Moscow',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# SQL-скрипт создания таблицы курсов лечения
CREATE_TREATMENT_COURSES_TABLE = """
CREATE TABLE IF NOT EXISTS treatment_courses (
    course_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    current_phase INTEGER DEFAULT 1 CHECK(current_phase BETWEEN 1 AND 5),
    current_character TEXT DEFAULT 'gaspode' 
        CHECK(current_character IN ('gaspode', 'nobby_colon', 'angua', 'carrot', 'vimes', 'vetinari', 'death')),
    status TEXT DEFAULT 'active' 
        CHECK(status IN ('active', 'completed', 'failed', 'paused')),
    smoking_quit_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# SQL-скрипт создания таблицы записей о приёме таблеток
CREATE_TABEX_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS tabex_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER REFERENCES treatment_courses(course_id) ON DELETE CASCADE,
    scheduled_time TIMESTAMP NOT NULL,
    actual_time TIMESTAMP,
    status TEXT DEFAULT 'scheduled' 
        CHECK(status IN ('scheduled', 'taken', 'missed', 'skipped')),
    phase INTEGER NOT NULL CHECK(phase BETWEEN 1 AND 5),
    character_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# SQL-скрипт создания таблицы взаимодействий с персонажами
CREATE_CHARACTER_INTERACTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS character_interactions (
    interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER REFERENCES treatment_courses(course_id) ON DELETE CASCADE,
    character_name TEXT NOT NULL 
        CHECK(character_name IN ('gaspode', 'nobby_colon', 'angua', 'carrot', 'vimes', 'vetinari', 'death')),
    interaction_type TEXT NOT NULL 
        CHECK(interaction_type IN ('greeting', 'reminder', 'encouragement', 'warning', 'farewell')),
    message_text TEXT NOT NULL,
    user_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# SQL-скрипты создания индексов для улучшения производительности
CREATE_INDEXES = """
-- Индекс для быстрого поиска пользователя по telegram_id
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);

-- Индекс для поиска активных курсов лечения
CREATE INDEX IF NOT EXISTS idx_treatment_courses_status ON treatment_courses(status);
CREATE INDEX IF NOT EXISTS idx_treatment_courses_user_id ON treatment_courses(user_id);

-- Индексы для логов приёма таблеток
CREATE INDEX IF NOT EXISTS idx_tabex_logs_course_id ON tabex_logs(course_id);
CREATE INDEX IF NOT EXISTS idx_tabex_logs_scheduled_time ON tabex_logs(scheduled_time);
CREATE INDEX IF NOT EXISTS idx_tabex_logs_status ON tabex_logs(status);

-- Индекс для взаимодействий с персонажами
CREATE INDEX IF NOT EXISTS idx_character_interactions_course_id ON character_interactions(course_id);
CREATE INDEX IF NOT EXISTS idx_character_interactions_character ON character_interactions(character_name);
"""

# Триггеры для автоматического обновления updated_at
CREATE_TRIGGERS = """
-- Триггер обновления updated_at для пользователей
CREATE TRIGGER IF NOT EXISTS update_users_updated_at
    AFTER UPDATE ON users
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE user_id = NEW.user_id;
END;

-- Триггер обновления updated_at для курсов лечения
CREATE TRIGGER IF NOT EXISTS update_treatment_courses_updated_at
    AFTER UPDATE ON treatment_courses
BEGIN
    UPDATE treatment_courses SET updated_at = CURRENT_TIMESTAMP WHERE course_id = NEW.course_id;
END;
"""


async def create_initial_schema() -> None:
    """Создает начальную схему базы данных."""
    db = get_db()
    
    logger.info("Создание схемы базы данных...")
    
    # Создаем таблицы
    tables = [
        ("users", CREATE_USERS_TABLE),
        ("treatment_courses", CREATE_TREATMENT_COURSES_TABLE),
        ("tabex_logs", CREATE_TABEX_LOGS_TABLE),
        ("character_interactions", CREATE_CHARACTER_INTERACTIONS_TABLE),
    ]
    
    for table_name, create_sql in tables:
        try:
            await db.execute_query(create_sql)
            logger.info(f"Таблица {table_name} создана/проверена")
        except Exception as e:
            logger.error(f"Ошибка создания таблицы {table_name}: {e}")
            raise
    
    # Создаем индексы
    try:
        await db.execute_script(CREATE_INDEXES)
        logger.info("Индексы созданы")
    except Exception as e:
        logger.error(f"Ошибка создания индексов: {e}")
        raise
    
    # Создаем триггеры
    try:
        await db.execute_script(CREATE_TRIGGERS)
        logger.info("Триггеры созданы")
    except Exception as e:
        logger.error(f"Ошибка создания триггеров: {e}")
        raise


async def check_schema_version() -> int:
    """
    Проверяет текущую версию схемы базы данных.
    
    Returns:
        Номер версии схемы (0, если таблица версий не существует)
    """
    db = get_db()
    
    # Проверяем существование таблицы schema_version
    if not await db.table_exists("schema_version"):
        # Создаем таблицу версий
        create_version_table = """
        CREATE TABLE schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO schema_version (version) VALUES (0);
        """
        await db.execute_script(create_version_table)
        return 0
    
    # Получаем текущую версию
    result = await db.fetch_one("SELECT MAX(version) as version FROM schema_version")
    return result['version'] if result and result['version'] else 0


async def update_schema_version(version: int) -> None:
    """
    Обновляет версию схемы базы данных.
    
    Args:
        version: Новый номер версии
    """
    db = get_db()
    await db.execute_query(
        "INSERT INTO schema_version (version) VALUES (?)",
        (version,)
    )
    logger.info(f"Версия схемы обновлена до {version}")


async def run_migrations() -> None:
    """Выполняет все необходимые миграции базы данных."""
    logger.info("Запуск миграций базы данных...")
    
    try:
        # Проверяем текущую версию схемы
        current_version = await check_schema_version()
        logger.info(f"Текущая версия схемы: {current_version}")
        
        # Версия 1: Создание базовых таблиц
        if current_version < 1:
            logger.info("Применение миграции 1: создание базовых таблиц")
            await create_initial_schema()
            await update_schema_version(1)
        
        # Здесь можно добавить новые миграции:
        # if current_version < 2:
        #     logger.info("Применение миграции 2: добавление новых колонок")
        #     await apply_migration_2()
        #     await update_schema_version(2)
        
        logger.info("Все миграции применены успешно")
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении миграций: {e}")
        raise


async def reset_database() -> None:
    """
    Полностью очищает и пересоздает базу данных.
    
    ВНИМАНИЕ: Эта функция удаляет ВСЕ данные!
    Использовать только для разработки и тестирования.
    """
    db = get_db()
    
    logger.warning("ВНИМАНИЕ: Полная очистка базы данных!")
    
    # Список всех таблиц для удаления
    tables_to_drop = [
        "character_interactions",
        "tabex_logs", 
        "treatment_courses",
        "users",
        "schema_version"
    ]
    
    # Удаляем все таблицы
    for table in tables_to_drop:
        await db.drop_table(table)
    
    # Пересоздаем схему
    await run_migrations()
    
    logger.info("База данных полностью пересоздана")
