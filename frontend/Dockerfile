# syntax=docker/dockerfile:1
# Arc control room — Next.js 15 (App Router). Multi-stage: install -> build ->
# minimal `next start` runner. Build context is ./frontend.
#
# Backend URL: BackendClient issues `${base}${path}`. With an EMPTY base the
# paths stay relative (/api/*, /health) and resolve to the page origin, which
# Caddy proxies to the backend. That keeps this image PORTABLE (no host/domain
# baked in). Override only if you serve the frontend WITHOUT the reverse proxy:
#   --build-arg NEXT_PUBLIC_ARC_BACKEND_URL=https://api.example.com

# 1. deps — full install (build needs the dev toolchain: TS, Tailwind, PostCSS)
FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# 2. build — compile with the (default empty) public backend base inlined
FROM node:22-slim AS build
WORKDIR /app
ARG NEXT_PUBLIC_ARC_BACKEND_URL=""
ENV NEXT_PUBLIC_ARC_BACKEND_URL=$NEXT_PUBLIC_ARC_BACKEND_URL \
    NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# 3. prod-deps — runtime-only node_modules for `next start`
FROM node:22-slim AS prod-deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# 4. runner — non-root, ships only what `next start` needs
FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000
COPY --from=prod-deps --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/.next ./.next
COPY --from=build --chown=node:node /app/public ./public
COPY --from=build --chown=node:node /app/package.json ./package.json
COPY --from=build --chown=node:node /app/next.config.ts ./next.config.ts
USER node
EXPOSE 3000
CMD ["npm", "run", "start"]
