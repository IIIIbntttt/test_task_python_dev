"""Схемы запросов для обработчиков XLSX-выгрузки."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.domain.enums import ProductionCountry


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
    min_price: float | None = Field(
        default=None,
        ge=0,
        description="Минимальная цена товара в рублях.",
    )
    max_price: float | None = Field(
        default=None,
        ge=0,
        description="Максимальная цена товара в рублях.",
    )
    min_rating: float | None = Field(
        default=None,
        ge=0,
        le=5,
        description="Минимальный рейтинг товара.",
    )
    max_rating: float | None = Field(
        default=None,
        ge=0,
        le=5,
        description="Максимальный рейтинг товара.",
    )
    production_country: ProductionCountry | None = Field(
        default=None,
        description="Фильтр по стране производства товара.",
    )

    @property
    def has_filters(self) -> bool:
        """Проверить, заданы ли дополнительные фильтры для итоговой выборки."""

        return any(
            value is not None and value != ""
            for value in (
                self.min_price,
                self.max_price,
                self.min_rating,
                self.max_rating,
                self.production_country,
            )
        )

    @property
    def search_limit(self) -> int:
        """Вернуть лимит кандидатов до применения пост-фильтрации."""

        if not self.has_filters:
            return self.limit
        if self.has_country_filter:
            return min(1500, max(self.limit * self.search_pages, self.limit * 2, 1000))
        return min(1000, max(self.limit * self.search_pages, self.limit * 2, 200))

    @property
    def search_pages(self) -> int:
        """Вернуть число страниц, которое стоит просканировать до фильтрации."""

        if not self.has_filters:
            return self.pages
        if self.has_country_filter:
            return 10
        return min(10, max(self.pages, 5))

    @property
    def has_country_filter(self) -> bool:
        """Проверить, задан ли фильтр по стране производства."""

        return self.production_country is not None

    @model_validator(mode="after")
    def validate_ranges(self) -> "CatalogExportParams":
        """Проверить корректность диапазонов цены и рейтинга."""

        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            raise ValueError("Минимальная цена не может быть больше максимальной.")

        if self.min_rating is not None and self.max_rating is not None and self.min_rating > self.max_rating:
            raise ValueError("Минимальный рейтинг не может быть больше максимального.")

        return self
