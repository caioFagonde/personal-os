FROM node:24-alpine

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@9.12.0 --activate

COPY . .

RUN pnpm install --no-frozen-lockfile

WORKDIR /app/apps/web

EXPOSE 9000

CMD ["pnpm", "dev"]
