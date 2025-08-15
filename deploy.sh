#!/bin/bash

# Скрипт развертывания VCD IP Manager

set -e

echo "🚀 VCD IP Manager Deployment Script"
echo "===================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker не установлен!${NC}"
    echo "Установите Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

# Проверка Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose не установлен!${NC}"
    echo "Установите Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Проверка .env файла
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env файл не найден!${NC}"
    echo "Создаю .env из .env.example..."
    cp .env.example .env
    echo -e "${RED}📝 Пожалуйста, отредактируйте .env файл и добавьте токены API!${NC}"
    exit 1
fi

# Создание необходимых директорий
echo "📁 Создание директорий..."
mkdir -p backend/logs
mkdir -p nginx/logs
mkdir -p ssl

# Опция выбора режима
echo ""
echo "Выберите режим развертывания:"
echo "1) Development (пересборка образов)"
echo "2) Production (использование существующих образов)"
echo -n "Выбор (1/2): "
read mode

case $mode in
    1)
        echo -e "${YELLOW}🔨 Сборка Docker образов...${NC}"
        docker-compose build --no-cache
        ;;
    2)
        echo -e "${GREEN}📦 Использование существующих образов...${NC}"
        ;;
    *)
        echo -e "${RED}Неверный выбор!${NC}"
        exit 1
        ;;
esac

# Остановка старых контейнеров
echo "🛑 Остановка старых контейнеров..."
docker-compose down

# Запуск контейнеров
echo -e "${GREEN}🚀 Запуск контейнеров...${NC}"
docker-compose up -d

# Ожидание запуска
echo "⏳ Ожидание запуска сервисов..."
sleep 10

# Проверка статуса
echo "🔍 Проверка статуса контейнеров..."
docker-compose ps

# Проверка здоровья backend
echo "💚 Проверка здоровья backend..."
if curl -f http://localhost/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend работает!${NC}"
else
    echo -e "${YELLOW}⚠️  Backend еще запускается...${NC}"
fi

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✅ Развертывание завершено!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "📊 Dashboard доступен по адресу: http://$(hostname -I | awk '{print $1}')"
echo "🔧 API документация: http://$(hostname -I | awk '{print $1}')/api/docs"
echo ""
echo "📝 Полезные команды:"
echo "  docker-compose logs -f        # Просмотр логов"
echo "  docker-compose restart        # Перезапуск сервисов"
echo "  docker-compose down           # Остановка сервисов"
echo "  docker-compose ps             # Статус контейнеров"
echo ""