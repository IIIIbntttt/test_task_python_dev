"""Настройки приложения и производные конфигурационные значения."""

from __future__ import annotations

from functools import cached_property

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str) -> tuple[str, ...]:
    """Разбить строку CSV на нормализованный кортеж значений."""

    return tuple(part.strip() for part in value.split(",") if part.strip())


class Settings(BaseSettings):
    """Настройки выполнения, загружаемые из переменных окружения и .env-файлов."""

    app_name: str = Field(default="Парсер каталога Wildberries")
    app_version: str = Field(default="1.0.0")
    default_query: str = Field(default="пальто из натуральной шерсти")
    default_pages: int = Field(default=1, ge=1, le=10)
    default_limit: int = Field(default=100, ge=1, le=500)

    wb_search_endpoints: str = Field(
        default=(
            "https://u-search.wb.ru/exactmatch/ru/common/v18/search,"
            "https://search.wb.ru/exactmatch/ru/common/v18/search,"
            "https://search.wb.ru/exactmatch/ru/common/v4/search"
        )
    )
    wb_card_detail_endpoints: str = Field(
        default=(
            "https://card.wb.ru/cards/v4/detail,"
            "https://card.wb.ru/cards/v2/detail,"
            "https://card.wb.ru/cards/detail"
        )
    )
    wb_destination: str = Field(default="-1257786")
    wb_currency: str = Field(default="rub")
    wb_locale: str = Field(default="ru")

    http_timeout_seconds: float = Field(default=20.0, gt=0)
    http_retries: int = Field(default=2, ge=0, le=5)
    http_max_connections: int = Field(default=40, ge=10, le=200)

    max_enrichment_concurrency: int = Field(default=12, ge=1, le=50)
    basket_shard_max: int = Field(default=30, ge=1, le=50)
    batch_size: int = Field(default=100, ge=1, le=500)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @cached_property
    def search_endpoints(self) -> tuple[str, ...]:
        """Вернуть настроенные search-endpoint-ы в виде нормализованного кортежа."""

        return _split_csv(self.wb_search_endpoints)

    @cached_property
    def card_detail_endpoints(self) -> tuple[str, ...]:
        """Вернуть настроенные endpoint-ы деталей карточек в виде нормализованного кортежа."""

        return _split_csv(self.wb_card_detail_endpoints)

    @cached_property
    def http_headers(self) -> dict[str, str]:
        """Собрать стандартные заголовки для публичных запросов к Wildberries."""

        return {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.wildberries.ru/",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        }
