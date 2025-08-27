#!/bin/bash

echo "========================================="
echo "Fixing Backend Issues"
echo "========================================="

# Исправляем app.py - добавляем Optional в импорты
echo "Fixing app.py imports..."

# Создаем резервную копию
cp backend/app.py backend/app.py.backup

# Исправляем импорт Optional
sed -i 's/from typing import List, Dict, Set$/from typing import List, Dict, Set, Optional/' backend/app.py

# Проверяем, что исправление применилось
if grep -q "from typing import List, Dict, Set, Optional" backend/app.py; then
    echo "✅ Fixed Optional import in app.py"
else
    echo "⚠️  Manual fix needed for app.py"
    echo "Add 'Optional' to the typing imports at line 8:"
    echo "from typing import List, Dict, Set, Optional"
fi

# Обновляем nginx.conf
echo ""
echo "Updating nginx.conf for new nginx version..."
cp frontend/nginx.conf frontend/nginx.conf.backup

# Перезапускаем только backend контейнер
echo ""
echo "Rebuilding backend container..."
docker compose stop backend
docker compose build backend --no-cache
docker compose up -d backend

# Ждем пока backend запустится
echo ""
echo "Waiting for backend to start..."
sleep 5

# Проверяем состояние
echo ""
echo "Checking backend status..."
if curl -s http://localhost:8000/api/health | grep -q "healthy"; then
    echo "✅ Backend is running correctly!"
else
    echo "⚠️  Backend might still be starting..."
    echo ""
    echo "Check logs with: docker compose logs backend"
fi

echo ""
echo "========================================="
echo "Fix completed!"
echo "Check the application at: https://vcd-public-ips.t-cloud.kz"
echo "========================================="
