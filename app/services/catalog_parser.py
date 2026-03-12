"""Сервис, который оркестрирует поиск, обогащение данных и генерацию XLSX."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.clients.wildberries import WildberriesClient
from app.domain.exceptions import CatalogNotFoundError
from app.domain.models import CatalogProduct, ContentCard, ExportedWorkbook
from app.schemas.catalog import CatalogExportParams
from app.services.xlsx_exporter import XlsxExporter
from app.utils.wildberries import (
    build_product_url,
    build_seller_url,
    country_matches,
    extract_characteristics,
    extract_country_of_origin,
    extract_description,
    extract_image_urls,
    extract_pics_count,
    extract_price,
    extract_rating,
    extract_reviews_count,
    extract_seller_id,
    extract_seller_name,
    extract_size_names,
    extract_stock,
    slugify_filename,
)


class CatalogParserService:
    """Объединить несколько payload-ов Wildberries в единый набор данных для экспорта."""

    def __init__(self, wb_client: WildberriesClient, xlsx_exporter: XlsxExporter) -> None:
        """Сохранить зависимости сервиса."""

        self._wb_client = wb_client
        self._xlsx_exporter = xlsx_exporter

    async def export_catalog(self, params: CatalogExportParams) -> ExportedWorkbook:
        """Собрать полную XLSX-выгрузку по переданным параметрам запроса."""

        products = await self._collect_products(
            query=params.query,
            pages=params.search_pages,
            limit=params.search_limit,
            sort=params.sort,
        )

        filtered_products = self._apply_filters(products, params)
        exported_products = filtered_products[: params.limit]
        if not exported_products:
            if not params.has_filters:
                raise CatalogNotFoundError("По указанному запросу товары не найдены.")

        workbook_content = self._xlsx_exporter.export(products=exported_products, query=params.query)
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename_suffix = slugify_filename(params.query) or "catalog"
        filename = f"wildberries_{filename_suffix}_{timestamp}.xlsx"

        return ExportedWorkbook(
            filename=filename,
            content=workbook_content,
            products_count=len(exported_products),
        )

    def _build_product(
        self,
        article_id: int,
        summary: Mapping[str, Any],
        detail: Mapping[str, Any] | None,
        content_card: ContentCard | None,
    ) -> CatalogProduct:
        """Нормализовать сырые payload-ы разных эндпоинтов в одну строку экспорта."""

        content_payload = content_card.payload if content_card is not None else None
        basket_host = content_card.basket_host if content_card is not None else None
        product_name = str(summary.get("name") or (detail.get("name") if detail else "") or "")

        seller_id = extract_seller_id(detail, summary, content_payload)
        return CatalogProduct(
            product_url=build_product_url(article_id),
            article=article_id,
            name=product_name,
            price=extract_price(detail, summary, content_payload),
            description=extract_description(content_payload),
            image_urls=extract_image_urls(
                article_id=article_id,
                basket_host=basket_host,
                pics_count=extract_pics_count(detail, summary, content_payload),
                content=content_payload,
            ),
            characteristics=extract_characteristics(content_payload),
            seller_name=extract_seller_name(detail, summary, content_payload),
            seller_url=build_seller_url(seller_id),
            sizes=extract_size_names(detail, summary, content_payload),
            stock=extract_stock(detail, summary, content_payload),
            rating=extract_rating(detail, summary, content_payload),
            reviews_count=extract_reviews_count(detail, summary, content_payload),
            production_country=extract_country_of_origin(content_payload, detail, summary),
        )

    def _apply_filters(
        self,
        products: list[CatalogProduct],
        params: CatalogExportParams,
    ) -> list[CatalogProduct]:
        """Отфильтровать товары по рейтингу, цене и стране производства."""

        filtered_products = products

        if params.min_price is not None:
            filtered_products = [
                product
                for product in filtered_products
                if product.price is not None and product.price >= params.min_price
            ]

        if params.max_price is not None:
            filtered_products = [
                product
                for product in filtered_products
                if product.price is not None and product.price <= params.max_price
            ]

        if params.min_rating is not None:
            filtered_products = [
                product
                for product in filtered_products
                if product.rating is not None and product.rating >= params.min_rating
            ]

        if params.max_rating is not None:
            filtered_products = [
                product
                for product in filtered_products
                if product.rating is not None and product.rating <= params.max_rating
            ]

        if params.production_country is not None:
            filtered_products = [
                product
                for product in filtered_products
                if country_matches(product.production_country, params.production_country)
            ]

        return filtered_products

    async def _collect_products(
        self,
        query: str,
        pages: int,
        limit: int,
        sort: str,
    ) -> list[CatalogProduct]:
        """Собрать нормализованные товары каталога из нескольких источников Wildberries."""

        summaries = await self._wb_client.search_catalog(
            query=query,
            pages=pages,
            limit=limit,
            sort=sort,
        )
        if not summaries:
            raise CatalogNotFoundError("По указанному запросу товары не найдены.")

        article_ids = [summary["id"] for summary in summaries if isinstance(summary.get("id"), int)]
        summaries_by_id = {summary["id"]: summary for summary in summaries if isinstance(summary.get("id"), int)}
        details_by_id = await self._wb_client.fetch_card_details(article_ids)
        content_cards_by_id = await self._wb_client.fetch_content_cards(article_ids, summaries_by_id, details_by_id)

        return [
            self._build_product(
                article_id=article_id,
                summary=summaries_by_id.get(article_id, {}),
                detail=details_by_id.get(article_id),
                content_card=content_cards_by_id.get(article_id),
            )
            for article_id in article_ids
        ]
