# Backend Dockerfile
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Создаем директории для логов
RUN mkdir -p /app/logs

# Создаем непривилегированного пользователя
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Экспорт порта
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Запуск приложения
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]