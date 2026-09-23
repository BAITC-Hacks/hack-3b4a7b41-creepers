# Электрокомплект AI-консультант

Frontend customer chat для ekt.kz / ТОО «Электрокомплект». Приложение помогает искать электротехнические товары, смотреть характеристики и наличие, находить альтернативы и явно подтверждать добавление товара в корзину.

## Стек

- Next.js App Router
- React 19
- TypeScript
- Tailwind CSS 4

## Запуск

```bash
npm install
copy .env.example .env.local
npm run dev
```

Откройте `http://localhost:3000`.

## Переменные окружения

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCKS=true
```

`NEXT_PUBLIC_USE_MOCKS=true` включает детерминированный demo flow без backend. Для реального backend укажите `false`. По умолчанию включён mock-режим, если переменная отсутствует, поэтому интерфейс запускается сразу после `npm install`.

## API-интеграция

Все запросы проходят только через собственный backend:

- `POST /api/chat`
- `GET /api/products/search?q=...`
- `GET /api/products/{id}`
- `POST /api/cart/prepare`
- `POST /api/cart/confirm`
- `GET /api/cart/{session_id}`

Клиент API находится в `lib/api.ts`. EKT API и Basic Auth credentials в frontend не используются. Session ID хранится локально в браузере и создаётся через `crypto.randomUUID()`.

## Demo flow

1. Отправьте «Мне нужен автомат на 25А».
2. Откройте характеристики или нажмите «Добавить».
3. Проверьте карточку подтверждения.
4. Нажмите «Подтвердить» и перейдите по checkout URL из ответа.

Mock-режим также демонстрирует альтернативный товар для запроса с «аналогом» или «отсутствующим» товаром.

## Проверка

```bash
npm run lint
npm run build
```

## Ограничения

- Вложения выбираются и отображаются в интерфейсе, но не отправляются в backend, пока backend API не объявит контракт обработки файлов.
- Поля товаров нормализованы под контракт задания; при изменении backend response нужно обновить типы в `types/` и адаптер в `lib/api.ts`.
- Frontend не хранит пользовательские данные, платежные данные или EKT credentials.This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
