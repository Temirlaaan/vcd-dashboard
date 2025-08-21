# --- Stage 1: Build React app ---
FROM node:18-alpine AS builder

WORKDIR /app

# Добавляем отладочную информацию
RUN echo "Node version:" && node --version
RUN echo "NPM version:" && npm --version

# Копируем только package.json сначала
COPY package.json ./

# Показываем содержимое файла
RUN echo "Package.json content:" && cat package.json

# Создаем package-lock.json если его нет
RUN npm install --package-lock-only

# Очищаем npm cache
RUN npm cache clean --force

# Устанавливаем зависимости с подробным выводом
RUN npm install --verbose

# Показываем что установилось
RUN ls -la node_modules/ | head -20

# Копируем остальные файлы
COPY . .

# Показываем структуру проекта
RUN echo "Project structure:" && ls -la

# Сборка с подробным выводом
RUN npm run build --verbose

# Показываем что получилось
RUN echo "Build output:" && ls -la build/

# --- Stage 2: Nginx ---
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

# Тестируем конфигурацию nginx
RUN nginx -t

# Открываем порты
EXPOSE 80 443

# Запуск nginx
CMD ["nginx", "-g", "daemon off;"]