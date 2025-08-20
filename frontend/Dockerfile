# --- Stage 1: Build React app ---
FROM node:22.9.0-alpine AS builder

WORKDIR /app

# Копируем только package.json и package-lock.json для кеширования зависимостей
COPY package*.json ./

# Устанавливаем зависимости (только продакшн)
RUN npm install --omit=dev

# Копируем остальной код
COPY . .

# Сборка production билда
RUN npm run build

# --- Stage 2: Nginx для раздачи статических файлов ---
FROM nginx:stable-alpine AS runner

# Копируем собранный build в nginx директорию
COPY --from=builder /app/build /usr/share/nginx/html

# Копируем кастомный nginx конфиг
COPY nginx/default.nginx.conf /etc/nginx/conf.d/default.conf

# Копируем SSL сертификаты
COPY nginx/ssl/t-cloud-2025.crt /etc/ssl/t-cloud-2025.crt
COPY nginx/ssl/t-cloud-2025.key /etc/ssl/t-cloud-2025.key

# Открываем порты
EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
