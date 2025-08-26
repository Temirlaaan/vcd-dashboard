# Frontend: build React app and serve with nginx
FROM node:18 AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.25-alpine
COPY --from=build /app/build /usr/share/nginx/html
# SPA fallback
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx-spa.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
