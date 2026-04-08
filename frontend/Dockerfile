# Multi-stage Dockerfile for React Frontend

# Stage 1: Build the React app
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

ARG VITE_API_SERVER_URL=
ENV VITE_API_SERVER_URL=${VITE_API_SERVER_URL}
RUN npm run build

# Stage 2: Development environment
FROM node:20-alpine AS development

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]

# Stage 3: Production environment
FROM nginx:alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

CMD ["nginx", "-g", "daemon off;"]
