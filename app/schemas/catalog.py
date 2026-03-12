"""Схемы запросов для обработчиков XLSX-выгрузки."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CatalogExportParams(BaseModel):
    """Параметры запроса, принимаемые endpoint-ом XLSX-выгрузки."""

    query: str = Field(
        default="пальто из натуральной шерсти",
        min_length=1,
        description="Поисковый запрос для каталога Wildberries.",
    )
    pages: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Количество страниц поисковой выдачи, которое нужно обработать.",
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Максимальное число товаров в выгрузке.",
    )
    sort: Literal["popular", "newly", "rate", "priceup", "pricedown"] = Field(
        default="popular",
        description="Сортировка поисковой выдачи Wildberries.",
    )
