"""
Главный модуль для запуска Табекс-бота.

Точка входа в приложение. Инициализирует и запускает бота с обработкой
системных сигналов для корректного завершения работы.
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.bot import TabexBot

logger = logging.getLogger(__name__)


async def main():
    """
    Главная функция запуска приложения.
    
    Создаёт экземпляр бота, регистрирует обработчики системных сигналов
    для graceful shutdown и запускает бота в бесконечном цикле.
    """
    # Создание экземпляра бота
    bot = TabexBot()
    
    # Обработчик для graceful shutdown
    def signal_handler(sig, frame):
        """Обработчик системных сигналов для корректной остановки бота."""
        logger.info(f"Получен сигнал {sig}, инициализация остановки бота...")
        asyncio.create_task(bot.stop())
    
    # Регистрация обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print("🚭 Запуск Табекс-бота...")
        print("📋 Для остановки используйте Ctrl+C")
        print("-" * 50)
        
        # Запуск бота
        await bot.run_forever()
        
    except KeyboardInterrupt:
        logger.info("Получено прерывание с клавиатуры")
    except Exception as e:
        logger.error(f"Критическая ошибка в main(): {e}")
        sys.exit(1)
    finally:
        print("\n" + "-" * 50)
        print("🛑 Табекс-бот остановлен")


if __name__ == "__main__":
    """
    Точка входа при запуске скрипта напрямую.
    
    Запускает main() в asyncio event loop с обработкой исключений.
    """
    try:
        # Запуск асинхронной main функции
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n⏹️  Остановка по запросу пользователя")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка при запуске: {e}")
        logging.error(f"Критическая ошибка при запуске: {e}")
        sys.exit(1)
