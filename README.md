# Парсер каталога Wildberries

FastAPI-приложение для выгрузки каталога Wildberries по поисковому запросу в `XLSX`.

Сервис собирает:

- ссылку на товар
- артикул
- название
- цену
- описание
- ссылки на изображения через запятую
- характеристики с сохранением структуры в JSON-формате внутри ячейки
- название селлера
- ссылку на селлера
- размеры товара через запятую
- суммарные остатки по товару
- рейтинг
- количество отзывов

## Стек

- `FastAPI` для HTTP API
- `httpx` для асинхронных запросов
- `openpyxl` для генерации `XLSX`
- `pydantic-settings` для конфигурации
- `Poetry` для управления зависимостями
- `ruff` для линтинга и сортировки импортов
- `mypy` для статической проверки типов
- `pre-commit` для автоматического запуска проверок перед коммитом

## Архитектура

```text
app/
  api/          HTTP-роуты и зависимости
  clients/      клиент публичных эндпоинтов Wildberries
  core/         конфигурация приложения
  domain/       доменные модели и исключения
  schemas/      pydantic-схемы API
  services/     orchestration + XLSX export
  utils/        функции нормализации данных
```

Основная логика разбита на слои:

1. `WildberriesClient` получает поисковую выдачу, batch-детали карточек и `card.json`.
2. `CatalogParserService` объединяет данные из нескольких источников в одну нормализованную модель.
3. `XlsxExporter` собирает финальный Excel-файл.

## Установка

Требования:

- Python `3.11+`

Основной способ установки через `Poetry`:

```bash
poetry install
cp .env.example .env
poetry run uvicorn app.main:app --reload
```

После запуска документация будет доступна по адресу:

- `http://127.0.0.1:8000/docs`

## Использование

Основной endpoint:

- `GET /api/v1/catalog/export`

Параметры:

- `query` — поисковый запрос
- `pages` — количество страниц выдачи
- `limit` — максимум товаров в выгрузке
- `sort` — сортировка выдачи
- `min_price` и `max_price` — диапазон цены в рублях
- `min_rating` и `max_rating` — диапазон рейтинга
- `production_country` — фильтр по стране производства из списка `Enum` в Swagger UI

Пример запроса:

```bash
curl -G "http://127.0.0.1:8000/api/v1/catalog/export" \
  --data-urlencode "query=пальто из натуральной шерсти" \
  --data-urlencode "pages=1" \
  --data-urlencode "limit=100" \
  -o wildberries_catalog.xlsx
```

Пример выборки с фильтрами:

```bash
curl -G "http://127.0.0.1:8000/api/v1/catalog/export" \
  --data-urlencode "query=пальто из натуральной шерсти" \
  --data-urlencode "min_price=15000" \
  --data-urlencode "max_price=30000" \
  --data-urlencode "min_rating=4.5" \
  --data-urlencode "production_country=Россия" \
  -o filtered_wildberries_catalog.xlsx
```

Healthcheck:

```bash
curl "http://127.0.0.1:8000/api/v1/health"
```

## Проверка качества кода

Команды для линтинга и типизации:

```bash
poetry run ruff check .
poetry run mypy app
```

Подключение `pre-commit`:

```bash
poetry run pre-commit install
```

Ручной запуск всех хуков:

```bash
poetry run pre-commit run --all-files
```

## Конфигурация

Основные переменные окружения:

- `WB_SEARCH_ENDPOINTS` — fallback-список поисковых endpoint-ов
- `WB_CARD_DETAIL_ENDPOINTS` — fallback-список endpoint-ов карточек
- `WB_DESTINATION` — региональный `dest`
- `HTTP_TIMEOUT_SECONDS` — таймаут запросов
- `HTTP_RETRIES` — число повторов на временных ошибках
- `MAX_ENRICHMENT_CONCURRENCY` — параллелизм обогащения карточек
- `BASKET_SHARD_MAX` — максимальный номер basket shard для резолва `card.json`

## Особенности реализации

- Используется асинхронный `httpx.AsyncClient` с connection pooling.
- Batch-запросы на `card detail` уменьшают число сетевых вызовов.
- Для `card.json` реализован fallback-резолв basket shard и кеширование по `volume`.
- Если часть дополнительных данных недоступна, файл все равно будет сформирован по уже собранным данным.

## Ограничения

- Сервис опирается на публичные внутренние endpoint-ы сайта Wildberries, а не на официальный seller API.
- Эти endpoint-ы могут менять формат, версию или ограничения без предупреждения.
- Из-за rate limit или антибот-защиты часть запросов может завершаться ошибками, особенно при больших объемах.

## Что можно улучшить дальше

- добавить тесты с моками `httpx`
- добавить сохранение файла на диск по отдельному endpoint
- добавить логирование и метрики
- добавить очередь задач для длинных выгрузок
