# The frontend image, built in two stages:
#   1. build - a Node image installs the packages and builds the React app into dist/
#   2. serve - a small nginx image serves those built files; Node is left behind
#
# nginx also forwards /api/... to the backend container, so the browser only ever talks
# to ONE address (no CORS needed). See nginx.conf.

# ---------- 1. build ----------
FROM node:22-alpine AS build
WORKDIR /app

# Packages first: re-used until package.json / package-lock.json change.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# VITE_API_URL stays empty: the app calls "/api/...", which nginx forwards.
RUN npm run build

# ---------- 2. serve ----------
# "unprivileged" = nginx that runs as a normal user (not root), listening on 8080.
FROM nginxinc/nginx-unprivileged:1.27-alpine AS serve
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
