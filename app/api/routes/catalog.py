"""Роуты для формирования XLSX-выгрузки по данным каталога Wildberries."""

from __future__ import annotations

from io import BytesIO
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_catalog_service
from app.domain.exceptions import CatalogNotFoundError, WildberriesClientError
from app.schemas.catalog import CatalogExportParams
from app.services.catalog_parser import CatalogParserService

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

router = APIRouter(tags=["Каталог"])


@router.get("/health", summary="Проверка состояния сервиса")
async def health_check() -> dict[str, str]:
    """Вернуть минимальный ответ для мониторинга и smoke-проверок."""

    return {"status": "ok"}


@router.get(
    "/catalog/export",
    summary="Скачать каталог в XLSX",
    response_description="XLSX-файл с данными каталога Wildberries",
)
async def export_catalog(
    query: str = Query(
        default="пальто из натуральной шерсти",
        min_length=1,
        description="Поисковый запрос для каталога Wildberries.",
    ),
    pages: int = Query(
        default=1,
        ge=1,
        le=10,
        description="Количество страниц поисковой выдачи, которое нужно обработать.",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Максимальное число товаров в выгрузке.",
    ),
    sort: Literal["popular", "newly", "rate", "priceup", "pricedown"] = Query(
        default="popular",
        description="Сортировка поисковой выдачи Wildberries.",
    ),
    service: CatalogParserService = Depends(get_catalog_service),
) -> StreamingResponse:
    """Собрать XLSX из поисковой выдачи Wildberries и отдать его потоком."""

    params = CatalogExportParams(query=query, pages=pages, limit=limit, sort=sort)
    try:
        exported_workbook = await service.export_catalog(params)
    except CatalogNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except WildberriesClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    headers = {
        "Content-Disposition": f'attachment; filename="{exported_workbook.filename}"',
        "X-Items-Count": str(exported_workbook.products_count),
    }

    return StreamingResponse(
        BytesIO(exported_workbook.content),
        media_type=XLSX_MEDIA_TYPE,
        headers=headers,
    )
