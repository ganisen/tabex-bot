#!/bin/bash

# Скрипт быстрого запуска Tabex Bot через Docker
# Автор: Tabex Bot Team

set -e  # Остановка при ошибках

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция вывода с цветом
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка зависимостей
check_dependencies() {
    print_status "Проверка системных зависимостей..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker не установлен. Установите Docker Desktop."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose не установлен."
        exit 1
    fi
    
    print_success "Все зависимости установлены"
}

# Проверка .env файла
check_env() {
    print_status "Проверка конфигурации..."
    
    if [ ! -f ".env" ]; then
        print_warning ".env файл не найден"
        
        if [ -f ".env.example" ]; then
            print_status "Создание .env из .env.example..."
            cp .env.example .env
            print_warning "ВНИМАНИЕ: Отредактируйте .env файл и укажите BOT_TOKEN!"
            print_warning "Получить токен можно у @BotFather в Telegram"
            
            # Открываем файл для редактирования
            if command -v nano &> /dev/null; then
                read -p "Открыть .env для редактирования? (y/n): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    nano .env
                fi
            fi
        else
            print_error ".env.example файл не найден"
            exit 1
        fi
    fi
    
    # Проверяем обязательные переменные
    source .env
    
    if [ -z "$BOT_TOKEN" ] || [ "$BOT_TOKEN" = "YOUR_BOT_TOKEN_HERE" ]; then
        print_error "BOT_TOKEN не настроен в .env файле"
        print_warning "Получите токен у @BotFather и укажите в .env файле"
        exit 1
    fi
    
    print_success "Конфигурация корректна"
}

# Создание необходимых директорий
create_directories() {
    print_status "Создание необходимых директорий..."
    
    mkdir -p data logs
    
    print_success "Директории созданы"
}

# Сборка и запуск
build_and_run() {
    print_status "Сборка Docker образа..."
    
    docker-compose build --no-cache
    
    print_success "Образ собран успешно"
    print_status "Запуск Tabex Bot..."
    
    docker-compose up -d
    
    print_success "🚭 Tabex Bot запущен!"
    print_status "Для просмотра логов: docker-compose logs -f tabex-bot"
    print_status "Для остановки: docker-compose down"
}

# Функция остановки
stop_bot() {
    print_status "Остановка Tabex Bot..."
    docker-compose down
    print_success "Bot остановлен"
}

# Функция просмотра логов
show_logs() {
    print_status "Логи Tabex Bot:"
    docker-compose logs -f tabex-bot
}

# Функция для показа статуса
show_status() {
    print_status "Статус контейнеров:"
    docker-compose ps
    echo
    print_status "Использование ресурсов:"
    docker stats --no-stream $(docker-compose ps -q) 2>/dev/null || echo "Контейнеры не запущены"
}

# Главная функция
main() {
    echo "🚭 Tabex Bot - Docker Management Script"
    echo "======================================="
    
    case "${1:-start}" in
        start)
            check_dependencies
            check_env
            create_directories
            build_and_run
            ;;
        stop)
            stop_bot
            ;;
        restart)
            stop_bot
            sleep 2
            check_env
            build_and_run
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        update)
            print_status "Обновление из git репозитория..."
            git pull origin main
            print_status "Пересборка контейнера..."
            docker-compose build --no-cache
            print_status "Перезапуск..."
            docker-compose down
            docker-compose up -d
            print_success "Обновление завершено!"
            ;;
        *)
            echo "Использование: $0 {start|stop|restart|logs|status|update}"
            echo ""
            echo "Команды:"
            echo "  start   - Запустить bot (по умолчанию)"
            echo "  stop    - Остановить bot"
            echo "  restart - Перезапустить bot"  
            echo "  logs    - Показать логи"
            echo "  status  - Показать статус"
            echo "  update  - Обновить из git и перезапустить"
            exit 1
            ;;
    esac
}

main "$@"
