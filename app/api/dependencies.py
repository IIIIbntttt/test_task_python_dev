"""Вспомогательные зависимости для обработчиков FastAPI."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from app.services.catalog_parser import CatalogParserService


def get_catalog_service(request: Request) -> CatalogParserService:
    """Вернуть сервис парсинга каталога, созданный при старте приложения."""

    return cast(CatalogParserService, request.app.state.catalog_service)
