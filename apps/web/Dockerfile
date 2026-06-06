FROM node:22-alpine
WORKDIR /app
RUN corepack enable
COPY package.json ./
RUN pnpm install --no-frozen-lockfile
COPY . .
EXPOSE 9000
CMD ["pnpm", "dev"]
