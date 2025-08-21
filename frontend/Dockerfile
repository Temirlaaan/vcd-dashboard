# --- Stage 1: Build React app ---
FROM node:18-alpine AS builder

WORKDIR /app

# Копируем package.json и package-lock.json
COPY package*.json ./

# Устанавливаем зависимости для production сборки
RUN npm ci --silent

# Копируем исходный код
COPY . .

# Сборка production билда
RUN npm run build

# --- Stage 2: Nginx для раздачи ---
FROM nginx:1.25-alpine AS runner

# Устанавливаем curl для healthcheck
RUN apk add --no-cache curl

# Удаляем дефолтную конфигурацию nginx
RUN rm /etc/nginx/conf.d/default.conf

# Копируем собранный React build
COPY --from=builder /app/build /usr/share/nginx/html

# Копируем нашу конфигурацию nginx
COPY nginx/default.nginx.conf /etc/nginx/conf.d/default.conf

# Создаем директории для логов и acme
RUN mkdir -p /var/log/nginx /var/www/acme

# Настраиваем права доступа
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html && \
    chown -R nginx:nginx /var/log/nginx

# Открываем порты
EXPOSE 80 443