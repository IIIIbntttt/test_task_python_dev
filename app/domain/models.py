"""Доменные сущности, используемые сервисами парсинга и экспорта."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ContentCard:
    """Дополнительный контент, загруженный из JSON карточки товара на basket-shard."""

    basket_host: str | None
    payload: dict[str, Any] | None


@dataclass(slots=True)
class CatalogProduct:
    """Нормализованная строка товара, которая попадет в XLSX-отчет."""

    product_url: str
    article: int
    name: str
    price: float | None
    description: str
    image_urls: list[str]
    characteristics: list[dict[str, Any]]
    seller_name: str
    seller_url: str
    sizes: list[str]
    stock: int
    rating: float | None
    reviews_count: int


@dataclass(slots=True)
class ExportedWorkbook:
    """Сериализованный XLSX-отчет и метаданные, нужные HTTP-слою."""

    filename: str
    content: bytes
    products_count: int
