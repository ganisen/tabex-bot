"""
Утилиты для обеспечения единственности экземпляра приложения.

Предотвращает запуск нескольких экземпляров бота одновременно
через механизм PID-файлов и файловых блокировок.
"""
import os
import sys
import fcntl
import tempfile
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SingletonLock:
    """
    Класс для обеспечения единственности экземпляра приложения.
    
    Использует файловые блокировки для предотвращения запуска
    нескольких экземпляров одного приложения одновременно.
    """
    
    def __init__(self, lock_name: str = "tabex-bot"):
        """
        Инициализация блокировки.
        
        Args:
            lock_name: Имя файла блокировки
        """
        self.lock_name = lock_name
        self.lock_file_path = None
        self.lock_file = None
    
    def __enter__(self):
        """Вход в контекстный менеджер - попытка захвата блокировки."""
        return self.acquire()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекстного менеджера - освобождение блокировки."""
        self.release()
    
    def acquire(self) -> bool:
        """
        Попытка захвата блокировки.
        
        Returns:
            True если блокировка захвачена успешно, False иначе
        """
        try:
            # Определяем путь к файлу блокировки
            if os.getenv('DOCKER_CONTAINER'):
                # В контейнере используем /tmp
                lock_dir = Path("/tmp")
            else:
                # Локально используем директорию проекта
                lock_dir = Path(__file__).parent.parent / "data"
                lock_dir.mkdir(exist_ok=True)
            
            self.lock_file_path = lock_dir / f"{self.lock_name}.lock"
            
            # Открываем файл для записи
            self.lock_file = open(self.lock_file_path, 'w')
            
            # Попытка захвата эксклюзивной блокировки без ожидания
            fcntl.lockf(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Записываем PID текущего процесса
            self.lock_file.write(str(os.getpid()))
            self.lock_file.flush()
            
            logger.info(f"Блокировка {self.lock_name} захвачена (PID: {os.getpid()})")
            return True
            
        except (IOError, OSError) as e:
            # Не удалось захватить блокировку
            if self.lock_file:
                self.lock_file.close()
                self.lock_file = None
            
            # Читаем PID уже работающего процесса
            existing_pid = self._get_existing_pid()
            if existing_pid:
                logger.error(f"Другой экземпляр {self.lock_name} уже работает (PID: {existing_pid})")
            else:
                logger.error(f"Не удалось захватить блокировку {self.lock_name}: {e}")
            
            return False
    
    def release(self):
        """Освобождение блокировки."""
        if self.lock_file:
            try:
                fcntl.lockf(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                logger.info(f"Блокировка {self.lock_name} освобождена")
            except Exception as e:
                logger.error(f"Ошибка при освобождении блокировки: {e}")
            finally:
                self.lock_file = None
        
        # Удаляем файл блокировки
        if self.lock_file_path and self.lock_file_path.exists():
            try:
                self.lock_file_path.unlink()
            except Exception as e:
                logger.warning(f"Не удалось удалить файл блокировки: {e}")
    
    def _get_existing_pid(self) -> Optional[int]:
        """
        Получает PID уже работающего процесса из файла блокировки.
        
        Returns:
            PID процесса или None если не удалось прочитать
        """
        if not self.lock_file_path or not self.lock_file_path.exists():
            return None
        
        try:
            with open(self.lock_file_path, 'r') as f:
                pid_str = f.read().strip()
                if pid_str.isdigit():
                    return int(pid_str)
        except Exception:
            pass
        
        return None
    
    def is_process_running(self, pid: int) -> bool:
        """
        Проверяет, работает ли процесс с указанным PID.
        
        Args:
            pid: ID процесса
            
        Returns:
            True если процесс работает, False иначе
        """
        try:
            os.kill(pid, 0)  # Сигнал 0 не убивает, только проверяет
            return True
        except OSError:
            return False


def ensure_single_instance(app_name: str = "tabex-bot") -> SingletonLock:
    """
    Обеспечивает единственность экземпляра приложения.
    
    Args:
        app_name: Имя приложения для блокировки
        
    Returns:
        SingletonLock объект для управления блокировкой
        
    Raises:
        SystemExit: Если не удалось захватить блокировку
    """
    lock = SingletonLock(app_name)
    
    if not lock.acquire():
        print(f"\n❌ Ошибка: экземпляр {app_name} уже запущен!")
        print("💡 Для решения проблемы:")
        print("   1. Остановите все запущенные экземпляры бота")
        print("   2. Выполните: docker-compose down")
        print("   3. Запустите заново: docker-compose up")
        print()
        sys.exit(1)
    
    return lock


def cleanup_stale_locks(app_name: str = "tabex-bot"):
    """
    Очищает устаревшие файлы блокировок (от завершившихся процессов).
    
    Args:
        app_name: Имя приложения
    """
    try:
        # Определяем путь к файлу блокировки
        if os.getenv('DOCKER_CONTAINER'):
            lock_dir = Path("/tmp")
        else:
            lock_dir = Path(__file__).parent.parent / "data"
        
        lock_file_path = lock_dir / f"{app_name}.lock"
        
        if not lock_file_path.exists():
            return
        
        # Читаем PID из файла
        with open(lock_file_path, 'r') as f:
            pid_str = f.read().strip()
        
        if not pid_str.isdigit():
            # Некорректный файл блокировки
            lock_file_path.unlink()
            logger.info("Удален некорректный файл блокировки")
            return
        
        pid = int(pid_str)
        
        # Проверяем, работает ли процесс
        try:
            os.kill(pid, 0)
            # Процесс работает, не трогаем блокировку
            logger.info(f"Найден активный процесс {app_name} (PID: {pid})")
        except OSError:
            # Процесс не работает, удаляем блокировку
            lock_file_path.unlink()
            logger.info(f"Удален устаревший файл блокировки (PID: {pid})")
            
    except Exception as e:
        logger.warning(f"Ошибка при очистке блокировок: {e}")
