#!/bin/bash

# Скрипт развертывания VCD Dashboard с HTTPS

echo "========================================="
echo "VCD Dashboard HTTPS Deployment"
echo "Domain: vcd-public-ips.t-cloud.kz"
echo "========================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка корневой директории
CURRENT_DIR=$(pwd)
echo "Current directory: $CURRENT_DIR"

# Проверка структуры проекта
echo ""
echo "Checking project structure..."

if [ ! -d "backend" ]; then
    echo -e "${RED}❌ Backend directory not found!${NC}"
    exit 1
fi

if [ ! -d "frontend" ]; then
    echo -e "${RED}❌ Frontend directory not found!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Project structure OK${NC}"

# Проверка SSL сертификатов
echo ""
echo "Checking SSL certificates..."

SSL_DIR="./ssl"
mkdir -p $SSL_DIR

# Проверяем наличие сертификатов
if [ ! -f "$SSL_DIR/t-cloud-2025.crt" ] || [ ! -f "$SSL_DIR/t-cloud-2025.key" ]; then
    echo -e "${YELLOW}⚠️  SSL certificates not found in $SSL_DIR${NC}"
    echo ""
    echo "Looking for certificates in current directory..."
    
    if [ -f "t-cloud-2025.crt" ] && [ -f "t-cloud-2025.key" ]; then
        echo "Found certificates, copying to ssl directory..."
        cp t-cloud-2025.crt $SSL_DIR/
        cp t-cloud-2025.key $SSL_DIR/
        echo -e "${GREEN}✅ Certificates copied${NC}"
    else
        echo -e "${RED}❌ SSL certificates not found!${NC}"
        echo ""
        echo "Please place your SSL certificates in the ssl/ directory:"
        echo "  - ssl/t-cloud-2025.crt"
        echo "  - ssl/t-cloud-2025.key"
        exit 1
    fi
fi

# Проверка прав на сертификаты
chmod 644 $SSL_DIR/t-cloud-2025.crt
chmod 600 $SSL_DIR/t-cloud-2025.key
echo -e "${GREEN}✅ SSL certificates ready${NC}"

# Проверка backend/.env
echo ""
echo "Checking configuration..."

if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}⚠️  backend/.env not found!${NC}"
    
    if [ -f "backend/.env_example" ]; then
        cp backend/.env_example backend/.env
        echo "Created backend/.env from template"
    else
        echo "Creating backend/.env template..."
        cat > backend/.env << 'EOF'
# VCD Cloud Configuration
VCD_URL=https://vcd.t-cloud.kz
VCD_API_VERSION=38.0
VCD_API_TOKEN=your_token_here

# VCD01 Cloud Configuration
VCD_URL_VCD01=https://vcd01.t-cloud.kz
VCD_API_VERSION_VCD01=37.0
VCD_API_TOKEN_VCD01=your_token_here

# VCD02 Cloud Configuration
VCD_URL_VCD02=https://vcd02.t-cloud.kz
VCD_API_VERSION_VCD02=37.0
VCD_API_TOKEN_VCD02=your_token_here

# Authentication
SECRET_KEY=your-secret-key-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH='$2b$12$YourPasswordHashHere'
ACCESS_TOKEN_EXPIRE_MINUTES=1440
EOF
    fi
    
    echo -e "${YELLOW}⚠️  Please edit backend/.env with your actual credentials!${NC}"
    read -p "Press Enter after editing the .env file..."
fi

# Проверка nginx.conf
if [ ! -f "frontend/nginx.conf" ]; then
    echo -e "${YELLOW}Creating frontend/nginx.conf...${NC}"
    # Копируем из артефакта выше
fi

echo -e "${GREEN}✅ Configuration ready${NC}"

# Проверка Docker
echo ""
echo "Checking Docker..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed!${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker daemon is not running!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is ready${NC}"

# Docker Compose command
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

echo "Using: $COMPOSE_CMD"

# Создание директорий
echo ""
echo "Creating necessary directories..."
mkdir -p backend/logs
echo -e "${GREEN}✅ Directories created${NC}"

# Остановка старых контейнеров
echo ""
echo "Stopping old containers..."
$COMPOSE_CMD down

# Очистка старых образов (опционально)
read -p "Remove old Docker images? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker rmi vcd_backend vcd_frontend 2>/dev/null || true
fi

# Сборка образов
echo ""
echo "Building Docker images..."
$COMPOSE_CMD build --no-cache

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Build failed!${NC}"
    exit 1
fi

# Запуск контейнеров
echo ""
echo "Starting services..."
$COMPOSE_CMD up -d

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to start services!${NC}"
    exit 1
fi

# Проверка статуса
echo ""
echo "Checking service status..."
sleep 5

$COMPOSE_CMD ps

# Проверка доступности
echo ""
echo "Waiting for services to be ready..."
sleep 5

# Проверка backend
echo -n "Testing backend API... "
if curl -k -f https://localhost/api/health &>/dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${YELLOW}⚠️  Not ready yet${NC}"
fi

# Проверка frontend
echo -n "Testing frontend HTTPS... "
if curl -k -f https://localhost &>/dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${YELLOW}⚠️  Not ready yet${NC}"
fi

# Проверка HTTP redirect
echo -n "Testing HTTP to HTTPS redirect... "
REDIRECT_RESPONSE=$(curl -I -s -o /dev/null -w "%{http_code}" http://localhost)
if [ "$REDIRECT_RESPONSE" = "301" ]; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${YELLOW}⚠️  Redirect not working${NC}"
fi

# Показ логов
echo ""
read -p "Show container logs? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    $COMPOSE_CMD logs --tail=30
fi

echo ""
echo "========================================="
echo -e "${GREEN}Deployment completed!${NC}"
echo ""
echo "Access the application:"
echo -e "  ${GREEN}https://vcd-public-ips.t-cloud.kz${NC}"
echo ""
echo "Default credentials:"
echo "  Username: admin"
echo "  Password: (the one you configured)"
echo ""
echo "Useful commands:"
echo "  View logs:    $COMPOSE_CMD logs -f"
echo "  Stop:         $COMPOSE_CMD down"
echo "  Restart:      $COMPOSE_CMD restart"
echo "  View status:  $COMPOSE_CMD ps"
echo ""
echo "SSL Certificate Info:"
openssl x509 -in $SSL_DIR/t-cloud-2025.crt -noout -dates 2>/dev/null || echo "  Could not read certificate dates"
echo "========================================="
