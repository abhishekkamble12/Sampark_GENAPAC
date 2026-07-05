# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency manifests first for better layer caching
COPY package.json package-lock.json ./

# Install exact dependencies defined in lockfile
RUN npm ci

# Copy remaining source files
COPY . .

# Build Vite/React app — output lands in /app/dist
RUN npm run build

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM nginx:alpine

# Remove the default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config (serves on port 8080 with SPA fallback)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy static assets produced by the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Deployment platforms (Render, Railway, etc.) expect port 8080
EXPOSE 8080

# Run nginx in the foreground so the container stays alive
CMD ["nginx", "-g", "daemon off;"]
