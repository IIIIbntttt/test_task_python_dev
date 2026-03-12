"""Точка входа FastAPI-приложения для сервиса парсинга Wildberries."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.catalog import router as catalog_router
from app.clients.wildberries import WildberriesClient
from app.core.config import Settings
from app.services.catalog_parser import CatalogParserService
from app.services.xlsx_exporter import XlsxExporter


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Создать и корректно освободить общие сервисы приложения."""

    settings = Settings()
    wb_client = WildberriesClient(settings)
    await wb_client.start()

    application.state.settings = settings
    application.state.wb_client = wb_client
    application.state.catalog_service = CatalogParserService(
        wb_client=wb_client,
        xlsx_exporter=XlsxExporter(),
    )

    try:
        yield
    finally:
        await wb_client.close()


def create_app() -> FastAPI:
    """Создать и настроить экземпляр FastAPI-приложения."""

    settings = Settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Сервис выгружает каталог Wildberries по поисковому запросу "
            "и формирует XLSX-файл."
        ),
        lifespan=lifespan,
    )
    application.include_router(catalog_router, prefix="/api/v1")
    return application


app = create_app()
