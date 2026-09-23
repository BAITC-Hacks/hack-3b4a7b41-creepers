# EKT Copilot — Frontend

Next.js + React + TypeScript. Чат, каталог, проверка характеристик, подтверждение, отдельная корзина, выгрузка списка и загрузка спецификаций.

## Запуск

```powershell
npm ci
npm run dev
```

Backend должен работать на `127.0.0.1:8000`. Браузер обращается к `/backend/*` через Next.js proxy. Для другого адреса создайте `.env.local` из `.env.example`, задайте `BACKEND_URL` и перезапустите Next.js. Ключи EKT/OpenAI во frontend не используются.

- `/` — реальные данные EKT.
- `/?mode=demo` — явно обозначенные синтетические данные backend, без ключей.
- `/cart/<session_id>?mode=demo` — текущая учебная корзина.

Активная реализация: `EktWorkspace`, `CatalogProduct`, `PurchaseCart`, `lib/workspace-api.ts`. Старые компоненты `ChatWindow` и `lib/api.ts` сохранены как предыдущая версия, но не используются страницами. Переменная `NEXT_PUBLIC_USE_MOCKS` на новый интерфейс не влияет.

Проверки: `npm run lint`, `npm run build`. Полный запуск, данные, ограничения, AI-ключ и сценарий жюри описаны в [корневом README](../README.md).