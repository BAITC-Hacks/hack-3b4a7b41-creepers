# Creepers AI — Backend для чата ekt.kz

Прототип HackAlem AI 2026, кейс №1. FastAPI предоставляет каталог, детерминированный русскоязычный ассистент и локальную корзину с обязательным подтверждением.

**Статус интеграции:** пароль EKT не предоставлен. Реальные ответы `/products`, `/products?page=2`, `/products/detail?id=515291` не получены. `EktResponseAdapter` намеренно возвращает `ekt_schema_unverified`: сопоставление полей и пагинация EKT не выдуманы. При пустом пароле возвращается `ekt_not_configured`. Бизнес-логика проверяется на явно синтетических тестовых данных; это не подтверждает работу с реальным каталогом. Для живого демо нужны и пароль, и завершённый адаптер после инспекции.

Проверка 23.09.2026: публичный запрос к `https://ekt.kz/api/products` без реквизитов получил HTTP 401. Запущенный Uvicorn отвечает `/health` и публикует все 10 путей OpenAPI. Синтетическое сквозное демо проходит, включая нулевой остаток и альтернативы.

## Стек и архитектура

Python 3.12+, FastAPI, Uvicorn, async httpx, Pydantic, pydantic-settings, python-dotenv. Тесты: pytest, pytest-asyncio, httpx MockTransport/ASGITransport.

```text
Backend/
  app/
    main.py, config.py
    api/       health, products, chat, cart
    clients/   ekt_client.py: HTTP Basic Auth, ошибки, единственная граница EKT JSON
    services/  products, stock, alternatives, sessions, cart, conditions
    agents/    intent.py (чистые правила), tools.py (фасад сервисов), assistant.py
    schemas/   нормализованные product, chat, cart, attachment
    core/      ошибки и настройка логирования
  scripts/     inspect_ekt.py, demo.py
  tests/       изолированные тесты без реальных реквизитов доступа
  .env.example, .gitignore, requirements.txt, pytest.ini
```

`API → assistant/service → EktClient → EKT`. Только сервис корзины меняет корзину. Сессии и ожидающие действия находятся в памяти; операции каждой сессии защищены одним async-lock. LLM и внешние AI-ключи не требуются. Русские фразы сосредоточены в intent/assistant/conditions, что позволяет добавить казахскую локализацию.

## Установка и запуск (PowerShell)

Из корня проекта:

```powershell
cd Backend
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
# Только если .env ещё нет; существующий файл не перезаписывать:
Copy-Item .env.example .env
# Впишите пароль локально в .env, не отправляйте его в чат и не коммитьте.
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Linux/macOS: `python3.12 -m venv .venv`, затем `.venv/bin/python -m pip install -r requirements.txt` и `.venv/bin/python -m uvicorn app.main:app --reload --port 8000`.

Swagger: <http://127.0.0.1:8000/docs>. OpenAPI: <http://127.0.0.1:8000/openapi.json>. `/health` подтверждает работу приложения, **не доступность EKT**.

## Переменные окружения

`.env` загружается относительно `Backend`, независимо от рабочей директории. Переменные процесса имеют приоритет.

| Переменная | Значение по умолчанию / назначение |
|---|---|
| `EKT_API_BASE_URL` | `https://ekt.kz/api`; только HTTPS без реквизитов в URL |
| `EKT_API_USERNAME` | `apiuser` |
| `EKT_API_PASSWORD` | Пусто; задаётся только локально |
| `CORS_ORIGINS` | `http://localhost:3000`; список через запятую |
| `DEMO_CHECKOUT_BASE_URL` | `http://localhost:3000` |
| `EKT_TIMEOUT_SECONDS` | 10 на HTTP-запрос |
| `CATALOG_MAX_PAGES` | 5 страниц на поиск, максимум 50 |
| `CATALOG_CACHE_SECONDS` | 60; кэш только страниц поиска |
| `CATALOG_SEARCH_TIMEOUT_SECONDS` | 8 на весь поиск, включая ожидание блокировки |
| `SESSION_TTL_SECONDS` | 3600 секунд бездействия |
| `MAX_SESSIONS` | 1000; при заполнении возвращается ошибка, активные корзины не вытесняются |
| `ATTACHMENT_MAX_BYTES` | 10485760 (10 MiB) |

## Подключение реального EKT API

1. Заполнить локальный `.env`.
2. Выполнить `.venv\Scripts\python.exe scripts/inspect_ekt.py`. Скрипт обращается только к трём документированным GET-запросам, выводит ключи/типы JSON и размеры массивов, не выводит значения полей, заголовки и пароль.
3. По реальным ответам реализовать Pydantic-модели wire-формата и `EktResponseAdapter.parse_page/parse_detail` **в `app/clients/ekt_client.py`**. Проверить идентификаторы, артикулы, категорию, семантику цены/валюты и остатка, характеристики, сертификаты и признак следующей страницы. Не угадывать, какой из остатков доступен для заказа, и не суммировать склады без подтверждения.
4. Добавить обезличенные реальные fixtures и тесты нормализации. `SyntheticAdapter` из тестов не копировать в production: он описывает исключительно тестовый формат.
5. Повторить инспекцию, запустить тесты и `scripts/demo.py` против работающего сервера.

Пустое поле в API остаётся `null`, `{}` или `[]` по контракту. Stock `0` → `out_of_stock`, положительный → `in_stock`, неизвестный → `unknown`. Неверные отрицательные значения отклоняются. Никакие реальные cart/search endpoints, не указанные партнёром, не используются.

## API-контракт для фронтенда

| Метод и путь | Запрос | Ответ |
|---|---|---|
| `GET /health` | — | `{"status":"ok"}` |
| `GET /api/products/search?q=25A` | `q`: 1–200 символов | `{products,query,scanned_pages,partial,message}` |
| `GET /api/products/{product_id}` | ID | Нормализованный `Product` |
| `GET /api/products/{product_id}/alternatives` | ID | `{product,alternatives:[{product,reason}],partial}` |
| `POST /api/chat` | `{session_id,message}` | Фиксированный контракт ниже |
| `POST /api/cart/prepare` | `{session_id,product_id,quantity}` | `{pending_confirmation:true,product,quantity,available_stock,message}` |
| `POST /api/cart/confirm` | `{session_id}` | `CartResponse` |
| `POST /api/cart/cancel` | `{session_id}` | `{message,cancelled,cart}` |
| `GET /api/cart/{session_id}` | session ID | `CartResponse`; неизвестная сессия → 404 |
| `POST /api/chat/attachments` | multipart: `session_id`, `file` | Только метаданные, `analyzed:false` |

`session_id`: 1–128 латинских букв, цифр, `_`, `-`. Фронтенд должен генерировать случайный UUID и сохранять его для всей беседы. Это идентификатор прототипа, а не полноценная авторизация. Product ID передаётся строкой. `quantity` — строго целое число 1–1000000, не строка и не boolean.

`Product`: `id`, `article`, `name`, `category`, `specifications` (словарь строк), `certificates` (массив строк), `price`, `currency`, `stock`, `availability`. `price`, `stock`, `available_stock` сериализуются десятичными **строками** или `null`, чтобы не терять точность. Валюта не подставляется по умолчанию.

Ответ чата:

```json
{
  "message": "...",
  "intent": "product_search",
  "products": [],
  "alternatives": [],
  "pending_confirmation": null,
  "cart": null,
  "checkout_url": null,
  "error": null
}
```

При подготовке `pending_confirmation` содержит объект ответа `/cart/prepare`. `cart` содержит `{items:[{product,quantity}],total_items,checkout_url}`. `total_items` — сумма количества, не число строк. Обработанные бизнес-ошибки чата возвращаются HTTP 200 с `error:{code,message}`; ошибки валидации — 422 с теми же полями контракта. Остальные API используют HTTP 4xx/5xx и `{error:{code,message}}`. Фронтенд должен проверять `error`, а не только HTTP-статус.

Ошибки включают: `ekt_not_configured`/`ekt_schema_unverified` (503), `ekt_timeout` (504), `ekt_unavailable` (503), `ekt_auth_error`/`ekt_http_error`/`ekt_invalid_json`/`ekt_invalid_product` (502), `product_not_found`/`session_not_found` (404), `insufficient_stock`/`stock_unknown`/`pending_action_missing`/`pending_action_expired` (409), `validation_error` (422). Реквизиты доступа и тело upstream-ошибки не возвращаются.

## Примеры запросов

После завершения реального адаптера:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod 'http://localhost:8000/api/products/search?q=25A'
Invoke-RestMethod http://localhost:8000/api/products/515291
Invoke-RestMethod http://localhost:8000/api/chat -Method Post -ContentType 'application/json; charset=utf-8' -Body '{"session_id":"demo-session","message":"Найди автомат 25А"}'
Invoke-RestMethod http://localhost:8000/api/cart/prepare -Method Post -ContentType application/json -Body '{"session_id":"demo-session","product_id":"515291","quantity":5}'
# Только после явного подтверждения пользователем:
Invoke-RestMethod http://localhost:8000/api/cart/confirm -Method Post -ContentType application/json -Body '{"session_id":"demo-session"}'
Invoke-RestMethod http://localhost:8000/api/cart/demo-session
Invoke-RestMethod http://localhost:8000/api/cart/cancel -Method Post -ContentType application/json -Body '{"session_id":"demo-session"}'
```

Не подключайте `/cart/confirm` к автоматическому эффекту или событию открытия чата: этот POST является отдельным явным действием пользователя.

## Корзина и подтверждение

1. Prepare читает свежую карточку, проверяет количество с учётом уже добавленного и сохраняет ожидающее действие. Корзина остаётся прежней.
2. Подтверждение в чате принимается только по точному списку: «да», «да, добавь», «подтверждаю», «подтверждаю добавление», «да, подтверждаю», `yes`, `confirm` и аналогичным перечисленным в `intent.py`. Вопросы и дополнительные условия не подтверждают действие.
3. Confirm повторно читает карточку и остаток. Неизвестного/недостаточного остатка достаточно для отказа. Успешное действие очищается сразу; повторный confirm не добавляет товар снова.
4. Ожидающее действие действует 5 минут. Смена выбранного товара, новая неоднозначная выдача поиска, отмена или неуспешная повторная подготовка отменяют старое действие. Недостаточный остаток при confirm также очищает действие. Транспортная ошибка оставляет действие для повторной попытки в пределах срока.

Это **локальная демонстрационная корзина**. Никакой резерв товара, заказ или оплата на ekt.kz не создаются. `http://localhost:3000/cart/{session_id}` — детерминированная ссылка для демонстрационного фронтенда; backend не реализует эту страницу, её наличие зависит от другого разработчика. Отдельного подтверждённого production cart API нет.

## Поиск, остатки и альтернативы

Поиск просматривает ограниченное число страниц; результаты дедуплицируются по ID, максимум 20 карточек. Страницы кэшируются с TTL, повторный поиск не скачивает каталог заново. `partial:true` означает, что не просмотрен весь каталог или выдача усечена. Отсутствие совпадения не означает отсутствие товара во всём EKT. Серверный поиск пока не подтверждён.

Stock-вопросы, карточки и операции корзины всегда идут за свежими данными. Поисковая выдача может содержать снимок остатка из TTL-кэша. Альтернативы требуют совпадения категории и характеристик/номинального тока; конфликтующие характеристики исключаются. Перед выдачей проверяется текущая доступность кандидатов, не более 5 параллельных карточек. Полная взаимозаменяемость не заявляется. Если данных недостаточно, альтернатив может не быть.

Оплата, доставка и минимальный заказ возвращают сообщение об отсутствии достоверных сведений. Проверенные партнёрские условия можно подключить отдельно в `conditions_service.py`.

## Вложения

Поддерживаемые расширения: `.xlsx`, `.xls`, `.docx`, `.doc`, `.pdf`, `.jpg`, `.jpeg`, `.png`. Принимается один multipart-файл до 10 MiB. Требуется Content-Length; chunked upload не поддерживается. Возвращаются безопасное базовое имя, размер и заявленный клиентом MIME type. Файл не анализируется, не выполняется, не сохраняется постоянно и не влияет на корзину. MIME/расширение не доказывают тип содержимого. Для будущего OCR/извлечения позиций нужен отдельный сервис с проверкой формата и подтверждением распознанных товаров.

## Тесты и демо

```powershell
.venv\Scripts\python.exe -m pytest -q
# Проверить HTTP-сервер на localhost:8000:
.venv\Scripts\python.exe scripts/smoke.py
# Полный сценарий на синтетических данных, без сетевого обращения к EKT:
.venv\Scripts\python.exe scripts/demo.py --synthetic
# После настройки и проверки реального адаптера, с запущенным сервером:
.venv\Scripts\python.exe scripts/inspect_ekt.py
.venv\Scripts\python.exe scripts/demo.py --base-url http://127.0.0.1:8000
```

Сценарий: «Мне нужен автомат на 25А» → выбор ID → наличие → характеристики → сертификат → «Добавь 5 штук» → пустая корзина → «Да, подтверждаю» → 5 единиц и demo URL. Отдельно проверяется нулевой остаток и альтернативы. Тесты также проверяют неизвестные данные, HTTP-ошибки, пагинацию, кэш, изменившийся остаток, изоляцию сессий, отмену и одновременные подтверждения.

## Безопасность и ограничения

- `.env`, `.venv`, временные файлы и логи исключены из Git. В примере окружения пароль пуст. Basic Auth используется только сервером; редиректы отключены, TLS проверяется.
- Пароли не входят в repr настроек, ответы, тестовые fixtures или логи. Не включайте HTTP debug-логирование в окружении с реальными реквизитами.
- Ввод валидируется; ошибки не отражают исходные значения. Платёжные данные не обрабатываются.
- Память процесса очищается при перезапуске. Запускать с **одним worker**; для нескольких процессов нужны общие сессии/хранилище и распределённая блокировка. `--reload` тоже сбрасывает корзины.
- Нет пользовательской авторизации, распределённых сессий, rate limiting, production checkout, резервирования и гарантий доставки запросов. Используйте как локальный хакатонный прототип.
- Реальная схема каталога и пагинация заблокированы до получения доступа. Тесты внутренних моделей не подменяют проверку реального EKT API.
- `Frontend/` не изменялся. Все исходники и документы этой реализации находятся в `Backend/`.
