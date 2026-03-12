"""Асинхронный клиент для публичных каталоговых эндпоинтов Wildberries."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import httpx

from app.core.config import Settings
from app.domain.exceptions import WildberriesClientError
from app.domain.models import ContentCard

LEGACY_BASKET_RANGES: tuple[tuple[int, int, int], ...] = (
    (0, 143, 1),
    (144, 287, 2),
    (288, 431, 3),
    (432, 719, 4),
    (720, 1007, 5),
    (1008, 1061, 6),
    (1062, 1115, 7),
    (1116, 1169, 8),
    (1170, 1313, 9),
    (1314, 1601, 10),
    (1602, 1655, 11),
    (1656, 1919, 12),
    (1920, 2045, 13),
)


class WildberriesClient:
    """Клиент, который агрегирует данные из нескольких неофициальных эндпоинтов Wildberries."""

    def __init__(self, settings: Settings) -> None:
        """Инициализировать клиент и переиспользуемое состояние выполнения."""

        self._settings = settings
        self._client: httpx.AsyncClient | None = None
        self._basket_host_cache: dict[int, str] = {}
        self._content_semaphore = asyncio.Semaphore(settings.max_enrichment_concurrency)

    @property
    def client(self) -> httpx.AsyncClient:
        """Вернуть инициализированный HTTP-клиент или завершиться ошибкой, если старт пропущен."""

        if self._client is None:
            raise RuntimeError("WildberriesClient is not started.")
        return self._client

    async def start(self) -> None:
        """Создать общий HTTP-клиент с пулом соединений."""

        if self._client is not None:
            return

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._settings.http_timeout_seconds),
            limits=httpx.Limits(
                max_connections=self._settings.http_max_connections,
                max_keepalive_connections=max(10, self._settings.http_max_connections // 2),
            ),
            follow_redirects=True,
            headers=self._settings.http_headers,
            http2=True,
        )

    async def close(self) -> None:
        """Закрыть общий HTTP-клиент."""

        if self._client is None:
            return

        await self._client.aclose()
        self._client = None

    async def search_catalog(
        self,
        query: str,
        pages: int,
        limit: int,
        sort: str,
    ) -> list[dict[str, Any]]:
        """Получить поисковую выдачу по запросу и вернуть уникальные товары."""

        products: list[dict[str, Any]] = []
        seen_articles: set[int] = set()
        for page in range(1, pages + 1):
            payload = await self._search_page(query=query, page=page, sort=sort)
            page_products = self._extract_products(payload)
            if not page_products:
                break

            for product in page_products:
                article_id = product.get("id")
                if not isinstance(article_id, int) or article_id in seen_articles:
                    continue

                seen_articles.add(article_id)
                products.append(product)
                if len(products) >= limit:
                    return products

        return products

    async def fetch_card_details(self, article_ids: Sequence[int]) -> dict[int, dict[str, Any]]:
        """Пакетно получить детали карточек сразу для нескольких артикулов."""

        batches = [
            article_ids[index : index + self._settings.batch_size]
            for index in range(0, len(article_ids), self._settings.batch_size)
        ]
        tasks = [self._fetch_card_detail_batch(batch) for batch in batches]
        payloads = await asyncio.gather(*tasks)

        details: dict[int, dict[str, Any]] = {}
        for payload in payloads:
            for product in self._extract_products(payload):
                article_id = product.get("id")
                if isinstance(article_id, int):
                    details[article_id] = product

        return details

    async def fetch_content_cards(
        self,
        article_ids: Sequence[int],
        summaries: Mapping[int, Mapping[str, Any]],
        details: Mapping[int, Mapping[str, Any]],
    ) -> dict[int, ContentCard]:
        """Получить content-card товаров с описаниями и структурированными характеристиками."""

        tasks = [
            self._fetch_single_content_card(
                article_id=article_id,
                summary=summaries.get(article_id),
                detail=details.get(article_id),
            )
            for article_id in article_ids
        ]
        content_cards = await asyncio.gather(*tasks)
        return {article_id: content_card for article_id, content_card in content_cards}

    async def _search_page(self, query: str, page: int, sort: str) -> dict[str, Any]:
        """Выполнить запрос одной страницы поисковой выдачи."""

        params = {
            "ab_testing": "false",
            "appType": 1,
            "curr": self._settings.wb_currency,
            "dest": self._settings.wb_destination,
            "lang": self._settings.wb_locale,
            "page": page,
            "query": query,
            "resultset": "catalog",
            "sort": sort,
            "spp": 30,
            "suppressSpellcheck": "false",
        }
        return await self._request_json_with_fallback(self._settings.search_endpoints, params=params)

    async def _fetch_card_detail_batch(self, article_ids: Sequence[int]) -> dict[str, Any]:
        """Загрузить payload с деталями карточек для пачки артикулов."""

        params = {
            "appType": 1,
            "curr": self._settings.wb_currency,
            "dest": self._settings.wb_destination,
            "locale": self._settings.wb_locale,
            "nm": ";".join(str(article_id) for article_id in article_ids),
            "spp": 30,
        }
        return await self._request_json_with_fallback(self._settings.card_detail_endpoints, params=params)

    async def _fetch_single_content_card(
        self,
        article_id: int,
        summary: Mapping[str, Any] | None,
        detail: Mapping[str, Any] | None,
    ) -> tuple[int, ContentCard]:
        """Определить basket-shard и получить content-card для одного артикула."""

        async with self._content_semaphore:
            payload, basket_host = await self._resolve_and_fetch_content(article_id, summary, detail)
            return article_id, ContentCard(basket_host=basket_host, payload=payload)

    async def _resolve_and_fetch_content(
        self,
        article_id: int,
        summary: Mapping[str, Any] | None,
        detail: Mapping[str, Any] | None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Перебирать кеш, подсказки и предполагаемые basket-host, пока не найдется content-card."""

        volume = article_id // 100000
        candidate_hosts: list[str] = []

        cached_host = self._basket_host_cache.get(volume)
        if cached_host is not None:
            candidate_hosts.append(cached_host)

        hinted_host = self._extract_basket_host_hint(summary, detail)
        if hinted_host is not None:
            candidate_hosts.append(hinted_host)

        # Wildberries регулярно меняет распределение volume по basket-shard,
        # поэтому сначала пробуем кеш и явные подсказки, а затем вероятные shard.
        guessed_host = self._guess_basket_host_number(volume)
        for shard_number in self._ordered_shard_numbers(guessed_host):
            candidate_hosts.append(f"basket-{shard_number:02d}.wbbasket.ru")

        for basket_host in self._dedupe_hosts(candidate_hosts):
            payload = await self._fetch_content_card_by_host(article_id, basket_host)
            if payload is None:
                continue

            self._basket_host_cache[volume] = basket_host
            return payload, basket_host

        return None, None

    async def _fetch_content_card_by_host(
        self,
        article_id: int,
        basket_host: str,
    ) -> dict[str, Any] | None:
        """Загрузить JSON content-card из конкретного basket-shard."""

        url = self._build_content_card_url(article_id, basket_host)
        try:
            response = await self.client.get(url)
        except httpx.HTTPError:
            return None

        if response.status_code != 200:
            return None

        try:
            payload = response.json()
        except ValueError:
            return None

        return dict(payload) if isinstance(payload, Mapping) else None

    async def _request_json_with_fallback(
        self,
        endpoints: Iterable[str],
        params: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Попробовать несколько версий эндпоинтов и повторить временные ошибки."""

        last_error: Exception | None = None
        for endpoint in endpoints:
            for attempt in range(self._settings.http_retries + 1):
                try:
                    response = await self.client.get(endpoint, params=params)
                    response.raise_for_status()
                    payload = response.json()
                except (httpx.HTTPError, ValueError) as error:
                    last_error = error
                    if attempt < self._settings.http_retries and self._should_retry(error):
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    break

                if isinstance(payload, Mapping):
                    return dict(payload)

                last_error = ValueError("Invalid JSON payload format.")
                break

        raise WildberriesClientError(
            "Не удалось получить корректный ответ от публичных эндпоинтов Wildberries."
        ) from last_error

    def _extract_products(self, payload: Mapping[str, Any]) -> list[dict[str, Any]]:
        """Извлечь список товаров из нескольких известных форматов ответа Wildberries."""

        data = payload.get("data")
        if isinstance(data, Mapping):
            products = data.get("products")
            if isinstance(products, list):
                return [dict(product) for product in products if isinstance(product, Mapping)]

        products = payload.get("products")
        if isinstance(products, list):
            return [dict(product) for product in products if isinstance(product, Mapping)]

        return []

    def _extract_basket_host_hint(
        self,
        *sources: Mapping[str, Any] | None,
    ) -> str | None:
        """Попробовать найти подсказку по basket-host внутри summary или detail payload."""

        direct_keys = (
            "basket",
            "basketHost",
            "basketId",
            "basket_id",
            "mediaBasket",
            "mediaHost",
            "mediaShard",
            "shard",
            "shardKey",
        )

        for source in sources:
            if not isinstance(source, Mapping):
                continue

            for key in direct_keys:
                basket_host = self._normalize_basket_host(source.get(key))
                if basket_host is not None:
                    return basket_host

            for nested_key in ("media", "meta", "tracking"):
                nested_source = source.get(nested_key)
                if not isinstance(nested_source, Mapping):
                    continue

                for key in direct_keys:
                    basket_host = self._normalize_basket_host(nested_source.get(key))
                    if basket_host is not None:
                        return basket_host

        return None

    def _normalize_basket_host(self, value: Any) -> str | None:
        """Преобразовать подсказку хоста в нормализованное имя basket-host."""

        if isinstance(value, int):
            return f"basket-{value:02d}.wbbasket.ru"

        if not isinstance(value, str):
            return None

        normalized = value.strip().removeprefix("https://").removeprefix("http://").strip("/")
        if not normalized:
            return None

        if normalized.isdigit():
            return f"basket-{int(normalized):02d}.wbbasket.ru"

        if normalized.startswith("basket-") and normalized.endswith(".wbbasket.ru"):
            return normalized

        if normalized.startswith("basket-") and ".wbbasket.ru" not in normalized:
            return f"{normalized}.wbbasket.ru"

        return None

    def _guess_basket_host_number(self, volume: int) -> int:
        """Вернуть наиболее вероятный shard на основе volume-сегмента товара."""

        for start, end, shard in LEGACY_BASKET_RANGES:
            if start <= volume <= end:
                return shard

        return min(max(round(volume / 165), 1), self._settings.basket_shard_max)

    def _ordered_shard_numbers(self, guessed_shard: int) -> list[int]:
        """Упорядочить кандидаты shard вокруг самого вероятного значения."""

        ordered: list[int] = []
        for delta in range(self._settings.basket_shard_max):
            for candidate in (guessed_shard + delta, guessed_shard - delta):
                if 1 <= candidate <= self._settings.basket_shard_max and candidate not in ordered:
                    ordered.append(candidate)

        return ordered

    def _build_content_card_url(self, article_id: int, basket_host: str) -> str:
        """Собрать URL content-card для конкретного basket-shard."""

        volume = article_id // 100000
        part = article_id // 1000
        return f"https://{basket_host}/vol{volume}/part{part}/{article_id}/info/ru/card.json"

    def _dedupe_hosts(self, hosts: Iterable[str]) -> list[str]:
        """Вернуть хосты без дубликатов, сохраняя исходный порядок."""

        deduped_hosts: list[str] = []
        seen_hosts: set[str] = set()
        for host in hosts:
            if host in seen_hosts:
                continue

            seen_hosts.add(host)
            deduped_hosts.append(host)

        return deduped_hosts

    def _should_retry(self, error: Exception) -> bool:
        """Определить временные транспортные и статусные ошибки, которые стоит повторить."""

        if isinstance(
            error,
            (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
            ),
        ):
            return True

        if isinstance(error, httpx.HTTPStatusError):
            return error.response.status_code in {429, 500, 502, 503, 504}

        return False
