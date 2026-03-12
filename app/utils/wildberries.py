"""Вспомогательные функции для нормализации payload-ов Wildberries в значения для экспорта."""

from __future__ import annotations

import html
import json
import re
from collections.abc import Mapping
from typing import Any

TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def build_product_url(article_id: int) -> str:
    """Собрать публичный URL страницы товара по идентификатору артикула."""

    return f"https://www.wildberries.ru/catalog/{article_id}/detail.aspx"


def build_seller_url(seller_id: int | None) -> str:
    """Собрать публичный URL страницы продавца или вернуть пустую строку, если его нет."""

    return f"https://www.wildberries.ru/seller/{seller_id}" if seller_id is not None else ""


def extract_price(*sources: Mapping[str, Any] | None) -> float | None:
    """Вернуть наиболее подходящую цену в рублях из нескольких вариантов payload."""

    sale_price_paths = (
        ("salePriceU",),
        ("extended", "clientPriceU"),
    )
    regular_price_paths = (
        ("priceU",),
        ("extended", "basicPriceU"),
    )

    for paths in (sale_price_paths, regular_price_paths):
        for source in sources:
            if not isinstance(source, Mapping):
                continue

            for path in paths:
                value = _get_nested(source, *path)
                normalized_price = normalize_price(value)
                if normalized_price is not None:
                    return normalized_price

    return None


def normalize_price(value: Any) -> float | None:
    """Преобразовать целочисленную цену WB в число с плавающей точкой в рублях."""

    if not isinstance(value, (int, float)):
        return None

    return round(float(value) / 100, 2)


def extract_description(content: Mapping[str, Any] | None) -> str:
    """Извлечь лучшее доступное описание товара из content-card."""

    if not isinstance(content, Mapping):
        return ""

    description_candidates = (
        content.get("description"),
        content.get("imt_text"),
        _get_nested(content, "details", "description"),
    )
    for candidate in description_candidates:
        cleaned_text = clean_text(candidate)
        if cleaned_text:
            return cleaned_text

    return ""


def extract_characteristics(content: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Извлечь характеристики, сохранив максимально близкую исходную структуру."""

    if not isinstance(content, Mapping):
        return []

    grouped_options = content.get("grouped_options") or content.get("groupedOptions")
    if isinstance(grouped_options, list):
        return [dict(item) for item in grouped_options if isinstance(item, Mapping)]

    characteristics = content.get("characteristics")
    if isinstance(characteristics, list):
        return [{"title": "characteristics", "items": list(characteristics)}]

    options = content.get("options")
    if isinstance(options, list):
        return [{"title": "options", "items": list(options)}]

    compositions = content.get("compositions")
    if isinstance(compositions, list):
        return [{"title": "compositions", "items": list(compositions)}]

    return []


def extract_seller_name(*sources: Mapping[str, Any] | None) -> str:
    """Извлечь название продавца из summary, detail или content payload."""

    for source in sources:
        if not isinstance(source, Mapping):
            continue

        for path in (("supplier",), ("selling", "supplier"), ("selling", "supplier_name")):
            value = _get_nested(source, *path)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return ""


def extract_seller_id(*sources: Mapping[str, Any] | None) -> int | None:
    """Извлечь идентификатор продавца из доступных payload."""

    for source in sources:
        if not isinstance(source, Mapping):
            continue

        for path in (("supplierId",), ("selling", "supplier_id")):
            value = _get_nested(source, *path)
            if isinstance(value, int):
                return value

    return None


def extract_size_names(*sources: Mapping[str, Any] | None) -> list[str]:
    """Собрать человекочитаемые названия размеров из доступных payload."""

    sizes: list[str] = []
    for source in sources:
        if not isinstance(source, Mapping):
            continue

        raw_sizes = source.get("sizes")
        if not isinstance(raw_sizes, list):
            continue

        for raw_size in raw_sizes:
            if not isinstance(raw_size, Mapping):
                continue

            size_name = _pick_size_name(raw_size)
            if size_name and size_name not in sizes:
                sizes.append(size_name)

    return sizes


def extract_stock(*sources: Mapping[str, Any] | None) -> int:
    """Посчитать суммарный остаток по размерам, вложенным stocks или totalQuantity."""

    fallback_total_quantity = 0
    for source in sources:
        if not isinstance(source, Mapping):
            continue

        raw_sizes = source.get("sizes")
        if isinstance(raw_sizes, list):
            stock = 0
            for raw_size in raw_sizes:
                if not isinstance(raw_size, Mapping):
                    continue

                nested_stocks = raw_size.get("stocks")
                if isinstance(nested_stocks, list):
                    stock += sum(
                        stock_item.get("qty", 0)
                        for stock_item in nested_stocks
                        if isinstance(stock_item, Mapping) and isinstance(stock_item.get("qty"), int)
                    )
                    continue

                quantity = raw_size.get("qty")
                if isinstance(quantity, int):
                    stock += quantity

            if stock > 0:
                return stock

        total_quantity = source.get("totalQuantity")
        if isinstance(total_quantity, int):
            fallback_total_quantity = max(fallback_total_quantity, total_quantity)

    return fallback_total_quantity


def extract_rating(*sources: Mapping[str, Any] | None) -> float | None:
    """Извлечь рейтинг товара из доступных payload."""

    for source in sources:
        if not isinstance(source, Mapping):
            continue

        for key in ("rating", "reviewRating", "nmReviewRating"):
            value = source.get(key)
            if isinstance(value, (int, float)):
                return float(value)

    return None


def extract_reviews_count(*sources: Mapping[str, Any] | None) -> int:
    """Извлечь количество отзывов из доступных payload."""

    for source in sources:
        if not isinstance(source, Mapping):
            continue

        for key in ("feedbacks", "feedbackCount", "nmFeedbacks"):
            value = source.get(key)
            if isinstance(value, int):
                return value

    return 0


def extract_pics_count(*sources: Mapping[str, Any] | None) -> int:
    """Извлечь количество изображений товара из summary, detail или content-данных."""

    fallback_pics_count = 0
    for source in sources:
        if not isinstance(source, Mapping):
            continue

        direct_value = source.get("pics")
        if isinstance(direct_value, int) and direct_value > 0:
            return direct_value
        if isinstance(direct_value, int):
            fallback_pics_count = max(fallback_pics_count, direct_value)

        for path in (
            ("media", "photo_count"),
            ("media", "photos_count"),
            ("media", "count"),
            ("media", "photosCount"),
        ):
            value = _get_nested(source, *path)
            if isinstance(value, int) and value > 0:
                return value
            if isinstance(value, int):
                fallback_pics_count = max(fallback_pics_count, value)

    return fallback_pics_count


def extract_image_urls(
    article_id: int,
    basket_host: str | None,
    pics_count: int,
    content: Mapping[str, Any] | None,
) -> list[str]:
    """Вернуть прямые URL изображений или восстановить их по basket-host и pics_count."""

    direct_urls = _extract_direct_image_urls(content)
    if direct_urls:
        return direct_urls

    if basket_host is None or pics_count <= 0:
        return []

    volume = article_id // 100000
    part = article_id // 1000
    return [
        f"https://{basket_host}/vol{volume}/part{part}/{article_id}/images/big/{image_index}.webp"
        for image_index in range(1, pics_count + 1)
    ]


def serialize_characteristics(characteristics: list[dict[str, Any]]) -> str:
    """Сериализовать структурированные характеристики в читаемую JSON-строку для Excel."""

    if not characteristics:
        return ""

    return json.dumps(characteristics, ensure_ascii=False, indent=2)


def slugify_filename(value: str) -> str:
    """Преобразовать произвольную строку в безопасный ASCII-фрагмент имени файла."""

    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.lower()).strip("_")
    return slug[:60]


def clean_text(value: Any) -> str:
    """Нормализовать HTML или обычный текст в одну компактную строку."""

    if not isinstance(value, str):
        return ""

    text = html.unescape(value)
    text = TAG_RE.sub(" ", text)
    return WHITESPACE_RE.sub(" ", text).strip()


def _extract_direct_image_urls(content: Mapping[str, Any] | None) -> list[str]:
    """Собрать прямые URL изображений из типовых медиа-структур внутри content-card."""

    if not isinstance(content, Mapping):
        return []

    candidates: list[str] = []
    for key in ("media", "photos", "images", "gallery"):
        candidates.extend(_collect_image_urls(content.get(key)))

    deduped_urls: list[str] = []
    seen_urls: set[str] = set()
    for url in candidates:
        if url in seen_urls:
            continue

        seen_urls.add(url)
        deduped_urls.append(url)

    return deduped_urls


def _collect_image_urls(node: Any) -> list[str]:
    """Рекурсивно извлечь URL изображений из вложенных медиа-структур."""

    if isinstance(node, str):
        normalized_url = node if node.startswith("http") else f"https:{node}" if node.startswith("//") else ""
        return [normalized_url] if _looks_like_image_url(normalized_url) else []

    if isinstance(node, Mapping):
        urls: list[str] = []
        for key in ("big", "large", "url", "src", "image", "origin"):
            value = node.get(key)
            if isinstance(value, str):
                normalized_url = value if value.startswith("http") else f"https:{value}" if value.startswith("//") else ""
                if _looks_like_image_url(normalized_url):
                    urls.append(normalized_url)

        for key in ("photos", "images", "items", "gallery"):
            urls.extend(_collect_image_urls(node.get(key)))

        return urls

    if isinstance(node, list):
        urls: list[str] = []
        for item in node:
            urls.extend(_collect_image_urls(item))
        return urls

    return []


def _looks_like_image_url(value: str) -> bool:
    """Проверить, похожа ли строка на URL изображения."""

    return value.startswith("http") and (
        value.endswith((".jpg", ".jpeg", ".png", ".webp"))
        or "/images/" in value
    )


def _pick_size_name(raw_size: Mapping[str, Any]) -> str:
    """Выбрать наиболее человекочитаемую метку размера из сырого payload размера."""

    for key in ("name", "origName", "optionName"):
        value = raw_size.get(key)
        if isinstance(value, str):
            normalized_value = value.strip()
            if normalized_value and normalized_value != "0":
                return normalized_value

    return ""


def _get_nested(source: Mapping[str, Any], *path: str) -> Any:
    """Безопасно пройти по вложенным словарям по указанному пути."""

    current: Any = source
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current
