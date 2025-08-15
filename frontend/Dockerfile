FROM node:18-alpine as builder

WORKDIR /app

# Update npm to the latest version
RUN npm install -g npm@11.5.2

COPY package*.json ./

RUN npm ci --omit=dev

COPY . .

RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/build /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]