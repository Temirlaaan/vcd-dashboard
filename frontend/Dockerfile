# --- Stage 1: Build React app ---
FROM node:18-alpine AS builder

WORKDIR /app

# Копируем package.json 
COPY package.json ./

# Устанавливаем зависимости (npm install вместо npm ci)
RUN npm install --silent --production=false

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

# Проверяем конфигурацию nginx при запуске
COPY <<EOF /docker-entrypoint.d/99-test-config.sh
#!/bin/sh
echo "Testing nginx configuration..."
nginx -t
if [ $? -ne 0 ]; then
    echo "Nginx configuration test failed!"
    exit 1
fi
echo "Nginx configuration test passed!"
EOF

RUN chmod +x /docker-entrypoint.d/99-test-config.sh

# Запуск nginx
CMD ["nginx", "-g", "daemon off;"]