# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY public ./public
COPY src ./src

# Set API URL environment variable (будет использоваться через HTTPS)
ENV REACT_APP_API_URL=https://vcd-public-ips.t-cloud.kz/api

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Install necessary packages
RUN apk add --no-cache openssl

# Copy built application
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create directory for logs
RUN mkdir -p /var/log/nginx

# Expose ports
EXPOSE 80 443

# Start nginx
CMD ["nginx", "-g", "daemon off;"]